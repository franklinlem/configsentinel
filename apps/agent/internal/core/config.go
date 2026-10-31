package core

import (
	"errors"
	"fmt"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
	"net"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

type File struct {
	Path     string `yaml:"path"`
	Alias    string `yaml:"alias"`
	HashOnly bool   `yaml:"hash_only"`
}
type Config struct {
	Agent struct {
		URL              string `yaml:"server_url"`
		ID               string `yaml:"agent_id"`
		TokenFile        string `yaml:"token_file"`
		Interval         int    `yaml:"interval_seconds"`
		MaxBytes         int64  `yaml:"max_file_bytes"`
		MaxFiles         int    `yaml:"max_files"`
		MaxQueue         int    `yaml:"max_queue_events"`
		QueueDB          string `yaml:"queue_db"`
		Batch            int    `yaml:"send_batch_size"`
		InsecureLoopback bool   `yaml:"allow_insecure_loopback"`
	} `yaml:"agent"`
	Monitoring struct {
		Files        []File   `yaml:"files"`
		DenyPrefixes []string `yaml:"deny_prefixes"`
		DenyGlobs    []string `yaml:"deny_globs"`
	} `yaml:"monitoring"`
}

var aliasPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$`)
var builtinPrefixes = []string{"/home", "/root", "/proc", "/sys", "/dev", "/run/secrets", "/var/lib/private"}
var builtinGlobs = []string{"*.env", ".env*", "*private*key*", "*.pem", "*.key", "*.p12", "*.pfx", "id_*", "*credentials*", "*secret*", "shadow", "shadow-", "*.dump"}

func Load(path string) (Config, error) {
	var c Config
	f, e := os.Open(path)
	if e != nil {
		return c, e
	}
	defer f.Close()
	d := yaml.NewDecoder(f)
	d.KnownFields(true)
	if e = d.Decode(&c); e != nil {
		return c, e
	}
	return c, c.Validate()
}
func (c *Config) Validate() error {
	if c.Agent.Interval == 0 {
		c.Agent.Interval = 60
	}
	if c.Agent.MaxBytes == 0 {
		c.Agent.MaxBytes = 10 << 20
	}
	if c.Agent.MaxFiles == 0 {
		c.Agent.MaxFiles = 100
	}
	if c.Agent.MaxQueue == 0 {
		c.Agent.MaxQueue = 10000
	}
	if c.Agent.Batch == 0 {
		c.Agent.Batch = 100
	}
	if c.Agent.Interval < 1 || c.Agent.Interval > 3600 || c.Agent.MaxBytes < 1 || c.Agent.MaxBytes > 100<<20 || c.Agent.MaxFiles < 1 || c.Agent.MaxFiles > 1000 || c.Agent.MaxQueue < 1 || c.Agent.MaxQueue > 100000 || c.Agent.Batch < 1 || c.Agent.Batch > 100 {
		return errors.New("limites de configuração inválidos")
	}
	if _, e := uuid.Parse(c.Agent.ID); e != nil {
		return errors.New("agent_id inválido")
	}
	u, e := url.Parse(c.Agent.URL)
	if e != nil || u.Host == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || strings.TrimRight(u.Path, "/") != "/api/v1" {
		return errors.New("server_url deve usar origem HTTPS e /api/v1")
	}
	if u.Scheme != "https" {
		ip := net.ParseIP(u.Hostname())
		if u.Scheme != "http" || !c.Agent.InsecureLoopback || ip == nil || !ip.IsLoopback() {
			return errors.New("TLS obrigatório; HTTP apenas em IP loopback explicitamente autorizado")
		}
	}
	for _, v := range []string{c.Agent.TokenFile, c.Agent.QueueDB} {
		if !filepath.IsAbs(v) || filepath.Clean(v) != v {
			return errors.New("token_file/queue_db devem ser absolutos")
		}
	}
	if len(c.Monitoring.Files) == 0 || len(c.Monitoring.Files) > c.Agent.MaxFiles {
		return errors.New("quantidade de arquivos inválida")
	}
	aliases, paths := map[string]bool{}, map[string]bool{}
	for _, f := range c.Monitoring.Files {
		if !f.HashOnly || !aliasPattern.MatchString(f.Alias) || aliases[f.Alias] || paths[f.Path] {
			return errors.New("hash_only obrigatório; aliases/paths devem ser únicos e válidos")
		}
		aliases[f.Alias] = true
		paths[f.Path] = true
		if e := c.CheckPath(f.Path); e != nil {
			return e
		}
	}
	return nil
}
func (c Config) CheckPath(path string) error {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path || strings.ContainsAny(path, "*?[]\x00") {
		return errors.New("somente paths absolutos individuais e normalizados")
	}
	prefixes := append(append([]string{}, builtinPrefixes...), c.Monitoring.DenyPrefixes...)
	for _, p := range prefixes {
		if path == p || strings.HasPrefix(path, strings.TrimRight(p, "/")+"/") {
			return errors.New("path bloqueado por política")
		}
	}
	globs := append(append([]string{}, builtinGlobs...), c.Monitoring.DenyGlobs...)
	for _, component := range strings.Split(strings.ToLower(path), "/") {
		for _, pattern := range globs {
			matched, e := filepath.Match(strings.ToLower(pattern), component)
			if e != nil {
				return fmt.Errorf("deny_glob inválido")
			}
			if matched {
				return errors.New("path sensível bloqueado")
			}
		}
	}
	return nil
}
