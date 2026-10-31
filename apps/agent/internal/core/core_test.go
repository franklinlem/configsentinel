//go:build linux

package core

import (
	"context"
	"errors"
	"github.com/google/uuid"
	"golang.org/x/sys/unix"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestSecureFilesystem(t *testing.T) {
	d := t.TempDir()
	path := filepath.Join(d, "demo.conf")
	if e := os.WriteFile(path, []byte("synthetic=true\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if s := Scan(path, 1024); s.State != "present" || len(s.Hash) != 64 {
		t.Fatalf("scan: %+v", s)
	}
	if s := Scan(path, 2); s.State != "unreadable" {
		t.Fatal("size limit")
	}
	if e := os.Symlink(path, filepath.Join(d, "link")); e != nil {
		t.Fatal(e)
	}
	if Scan(filepath.Join(d, "link"), 1024).State != "unreadable" {
		t.Fatal("symlink followed")
	}
	sub := filepath.Join(d, "sub")
	os.Mkdir(sub, 0700)
	os.WriteFile(filepath.Join(sub, "file"), []byte("fixture"), 0600)
	os.Symlink(sub, filepath.Join(d, "parent-link"))
	if Scan(filepath.Join(d, "parent-link/file"), 1024).State != "unreadable" {
		t.Fatal("intermediate symlink")
	}
	os.Link(path, filepath.Join(d, "hardlink"))
	if Scan(path, 1024).State != "unreadable" {
		t.Fatal("hardlink allowed")
	}
	fifo := filepath.Join(d, "fifo")
	if e := unix.Mkfifo(fifo, 0600); e != nil {
		t.Fatal(e)
	}
	if Scan(fifo, 1024).State != "unreadable" {
		t.Fatal("FIFO allowed")
	}
	if Scan(d, 1024).State != "unreadable" {
		t.Fatal("directory allowed")
	}
	if Scan(filepath.Join(d, "absent"), 1024).State != "missing" {
		t.Fatal("missing misclassified")
	}
}
func TestPolicy(t *testing.T) {
	c := Config{}
	for _, path := range []string{"/home/test/x", "/root/x", "/proc/self/environ", "/tmp/.env.production", "/tmp/private-key.conf", "/tmp/demo.pem", "/tmp/a/../x", "relative", "/tmp/*.conf", "/tmp/id_rsa"} {
		if c.CheckPath(path) == nil {
			t.Fatalf("allowed %s", path)
		}
	}
	if e := c.CheckPath("/tmp/configsentinel-demo.conf"); e != nil {
		t.Fatal(e)
	}
}
func TestTransitions(t *testing.T) {
	a := Snapshot{State: "present", Hash: strings.Repeat("a", 64), Ever: true}
	b := a
	b.Hash = strings.Repeat("b", 64)
	cases := []struct {
		old, now Snapshot
		want     string
	}{{Snapshot{}, a, "baseline"}, {a, a, ""}, {a, b, "modified"}, {a, Snapshot{State: "missing"}, "deleted"}, {Snapshot{State: "missing", Ever: true}, a, "restored"}, {Snapshot{State: "missing"}, a, "created"}, {a, Snapshot{State: "unreadable"}, "unreadable"}, {Snapshot{State: "unreadable", Hash: a.Hash}, a, "recovered"}, {Snapshot{State: "unreadable", Hash: a.Hash}, b, "modified"}, {Snapshot{}, Snapshot{State: "missing"}, "missing_initial"}}
	for _, c := range cases {
		if got, _ := Transition(c.old, c.now); got != c.want {
			t.Fatalf("got %s want %s", got, c.want)
		}
	}
}
func TestDurableQueueAndSaturation(t *testing.T) {
	path := filepath.Join(t.TempDir(), "queue.sqlite")
	aid := uuid.NewString()
	q, e := OpenQueue(path, aid, 1)
	if e != nil {
		t.Fatal(e)
	}
	a := Snapshot{State: "present", Hash: strings.Repeat("a", 64), Ever: true}
	b := a
	b.Hash = strings.Repeat("b", 64)
	if e = q.Observe("demo", a, time.Now().UTC()); e != nil {
		t.Fatal(e)
	}
	if !errors.Is(q.Observe("demo", b, time.Now().UTC()), ErrFull) {
		t.Fatal("full queue advanced")
	}
	events, _ := q.Pending(100)
	first := events[0]
	q.DB.Close()
	q, e = OpenQueue(path, aid, 1)
	if e != nil {
		t.Fatal(e)
	}
	defer q.DB.Close()
	events, _ = q.Pending(100)
	if events[0].UUID != first.UUID {
		t.Fatal("event lost on restart")
	}
	if e = q.Ack([]string{first.UUID}); e != nil {
		t.Fatal(e)
	}
	if e = q.Observe("demo", b, time.Now().UTC()); e != nil {
		t.Fatal(e)
	}
	events, _ = q.Pending(100)
	if len(events) != 1 || events[0].Kind != "modified" || events[0].Sequence != 2 {
		t.Fatalf("snapshot/sequence not transactional: %+v", events)
	}
	q.DB.Close()
	if bad, e := OpenQueue(path, uuid.NewString(), 1); e == nil {
		bad.DB.Close()
		t.Fatal("agent identity changed")
	}
}
func TestTransportRejectsCommands(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(202)
		w.Write([]byte(`{"accepted":[],"duplicates":[],"rejected":[],"command":"read_file"}`))
	}))
	defer server.Close()
	d := t.TempDir()
	token := filepath.Join(d, "agent.token")
	os.WriteFile(token, []byte("cs_"+strings.Repeat("x", 43)), 0600)
	c := Config{}
	c.Agent.URL = server.URL
	c.Agent.TokenFile = token
	c.Agent.Batch = 100
	q, e := OpenQueue(filepath.Join(d, "queue.sqlite"), uuid.NewString(), 10)
	if e != nil {
		t.Fatal(e)
	}
	defer q.DB.Close()
	q.Observe("fixture", Snapshot{State: "present", Hash: strings.Repeat("a", 64), Ever: true}, time.Now().UTC())
	if NewTransport(c).Flush(context.Background(), q) == nil {
		t.Fatal("command accepted")
	}
	if n, _ := q.Depth(); n != 1 {
		t.Fatal("event lost")
	}
}

func TestConfigurationValidation(t *testing.T) {
	valid := func() Config {
		var c Config
		c.Agent.ID = uuid.NewString()
		c.Agent.URL = "https://example.test/api/v1"
		c.Agent.TokenFile = "/etc/configsentinel/agent.token"
		c.Agent.QueueDB = "/var/lib/configsentinel/queue.sqlite"
		c.Monitoring.Files = []File{{Path: "/opt/configsentinel-lab/demo.conf", Alias: "demo", HashOnly: true}}
		return c
	}
	c := valid()
	if e := c.Validate(); e != nil {
		t.Fatal(e)
	}
	for _, change := range []func(*Config){func(c *Config) { c.Agent.URL = "http://example.test/api/v1" }, func(c *Config) { c.Agent.MaxQueue = -1 }, func(c *Config) { c.Agent.Batch = 101 }, func(c *Config) { c.Agent.ID = "invalid" }, func(c *Config) { c.Agent.QueueDB = "relative" }, func(c *Config) { c.Monitoring.Files[0].HashOnly = false }, func(c *Config) { c.Monitoring.Files = append(c.Monitoring.Files, c.Monitoring.Files[0]) }, func(c *Config) { c.Monitoring.Files[0].Path = "/tmp/.env" }, func(c *Config) { c.Agent.URL = "https://user:password@example.test/api/v1" }, func(c *Config) { c.Agent.URL = "https://example.test/api/v1?token=secret" }} {
		c := valid()
		change(&c)
		if c.Validate() == nil {
			t.Fatal("unsafe configuration accepted")
		}
	}
	c = valid()
	c.Agent.URL = "http://127.0.0.1:8080/api/v1"
	c.Agent.InsecureLoopback = true
	if e := c.Validate(); e != nil {
		t.Fatal(e)
	}
}
func TestSymlinkSwapDoesNotReadTarget(t *testing.T) {
	d := t.TempDir()
	path := filepath.Join(d, "watched.conf")
	canary := filepath.Join(d, "canary.conf")
	os.WriteFile(canary, []byte("synthetic-canary-not-to-be-read"), 0600)
	for i := 0; i < 100; i++ {
		os.Remove(path)
		os.Symlink(canary, path)
		if s := Scan(path, 1024); s.Hash != "" || s.State != "unreadable" {
			t.Fatal("symlink canary read")
		}
		os.Remove(path)
		os.WriteFile(path, []byte("synthetic-allowed"), 0600)
		if s := Scan(path, 1024); s.State != "present" {
			t.Fatal("regular fixture rejected")
		}
	}
}
