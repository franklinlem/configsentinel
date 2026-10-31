//go:build linux

package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"github.com/franklinlem/configsentinel/apps/agent/internal/core"
	"golang.org/x/sys/unix"
	"log/slog"
	"math/rand/v2"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
	if e := run(); e != nil {
		slog.Error("agent stopped", "error", e)
		os.Exit(1)
	}
}
func run() error {
	path := flag.String("config", "/etc/configsentinel/agent.yaml", "configuração local")
	once := flag.Bool("once", false, "um ciclo de laboratório")
	flag.Parse()
	if os.Geteuid() == 0 {
		return syscall.EPERM
	}
	c, e := core.Load(*path)
	if e != nil {
		return e
	}
	if e = os.MkdirAll(filepath.Dir(c.Agent.QueueDB), 0700); e != nil {
		return e
	}
	lock, e := os.OpenFile(c.Agent.QueueDB+".lock", os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return e
	}
	defer lock.Close()
	if e = unix.Flock(int(lock.Fd()), unix.LOCK_EX|unix.LOCK_NB); e != nil {
		return e
	}
	q, e := core.OpenQueue(c.Agent.QueueDB, c.Agent.ID, c.Agent.MaxQueue)
	if e != nil {
		return e
	}
	defer q.DB.Close()
	policyJSON, _ := json.Marshal(c.Monitoring)
	policyHash := sha256.Sum256(policyJSON)
	slog.Info("local policy loaded", "files", len(c.Monitoring.Files), "hash_only", true, "policy_sha256", hex.EncodeToString(policyHash[:]))
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	transport := core.NewTransport(c)
	var observed time.Time
	var nextSend time.Time
	backoff := time.Second
	for {
		start := time.Now().UTC()
		ok := true
		for _, f := range c.Monitoring.Files {
			if ctx.Err() != nil {
				return nil
			}
			snapshot := core.Scan(f.Path, c.Agent.MaxBytes)
			if e = q.Observe(f.Alias, snapshot, start); e != nil {
				ok = false
				slog.Error("observation not committed", "alias", f.Alias, "error", e)
			}
		}
		if ok {
			observed = start
		}
		if !time.Now().Before(nextSend) {
			e = transport.Flush(ctx, q)
			if e == nil {
				e = transport.Heartbeat(ctx, q, observed)
			}
			if e != nil {
				slog.Warn("delivery deferred", "error", e)
				nextSend = time.Now().Add(backoff + time.Duration(rand.Int64N(int64(backoff/2+1))))
				backoff = min(backoff*2, 5*time.Minute)
			} else {
				backoff = time.Second
				nextSend = time.Time{}
			}
		}
		if *once {
			return e
		}
		timer := time.NewTimer(time.Duration(c.Agent.Interval) * time.Second)
		select {
		case <-ctx.Done():
			timer.Stop()
			return nil
		case <-timer.C:
		}
	}
}
