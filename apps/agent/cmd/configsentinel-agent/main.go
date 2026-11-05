//go:build linux

package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"github.com/franklinlem/configsentinel/apps/agent/internal/core"
	"golang.org/x/sys/unix"
	"log/slog"
	"os"
	"os/signal"
	"sync/atomic"
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
	lock, e := core.OpenStateFile(c.Agent.QueueDB + ".lock")
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
	observed, e := q.LastObserved()
	if e != nil {
		return e
	}
	wake := make(chan struct{}, 1)
	heartbeatWake := make(chan struct{}, 1)
	done := make(chan struct{})
	var observedUnix atomic.Int64
	if !observed.IsZero() {
		observedUnix.Store(observed.UnixNano())
	}
	if !*once {
		heartbeatDone := make(chan struct{})
		go func() { defer close(done); transport.RunFlush(ctx, q, wake) }()
		go func() {
			defer close(heartbeatDone)
			transport.RunHeartbeat(ctx, q, func() time.Time {
				n := observedUnix.Load()
				if n == 0 {
					return time.Time{}
				}
				return time.Unix(0, n).UTC()
			}, time.Duration(c.Agent.Interval)*time.Second, heartbeatWake)
		}()
		defer func() { stop(); <-done; <-heartbeatDone }()
	}
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
			if e = q.RecordObserved(start); e != nil {
				return e
			}
			observed = start
			observedUnix.Store(start.UnixNano())
			select {
			case heartbeatWake <- struct{}{}:
			default:
			}
		}
		if *once {
			// Even one-shot lab runs exercise delivery and heartbeat independently.
			result := make(chan error, 1)
			go func() { result <- transport.Flush(ctx, q) }()
			heartbeatError := transport.Heartbeat(ctx, q, observed)
			return errors.Join(heartbeatError, <-result)
		}
		select {
		case wake <- struct{}{}:
		default:
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
