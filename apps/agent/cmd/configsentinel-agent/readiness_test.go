//go:build linux

package main

import (
	"encoding/json"
	"flag"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/franklinlem/configsentinel/apps/agent/internal/core"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
)

// Exercises the actual --once runner against a synthetic central, then recovery.
func TestReadinessRunnerHeartbeatUnderIngestionFailure(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("agent intentionally refuses root")
	}
	var failed atomic.Bool
	failed.Store(true)
	var heartbeats atomic.Int64
	central := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v1/agent/heartbeat" {
			heartbeats.Add(1)
			w.WriteHeader(202)
			_, _ = w.Write([]byte(`{"ok":true,"server_time":"2026-10-31T00:00:00Z","clock_skew_warning":false}`))
			return
		}
		if failed.Load() {
			w.WriteHeader(503)
			return
		}
		var batch struct {
			Events []core.Event `json:"events"`
		}
		if err := json.NewDecoder(r.Body).Decode(&batch); err != nil {
			w.WriteHeader(422)
			return
		}
		accepted := []string{}
		for _, event := range batch.Events {
			accepted = append(accepted, event.UUID)
		}
		w.WriteHeader(202)
		_ = json.NewEncoder(w).Encode(map[string]any{"accepted": accepted, "duplicates": []string{}, "rejected": []string{}})
	}))
	defer central.Close()
	dir := t.TempDir()
	var c core.Config
	c.Agent.URL = central.URL + "/api/v1"
	c.Agent.ID = uuid.NewString()
	c.Agent.TokenFile = filepath.Join(dir, "agent.token")
	c.Agent.QueueDB = filepath.Join(dir, "queue.sqlite")
	c.Agent.InsecureLoopback = true
	fixture := filepath.Join(dir, "fixture.conf")
	c.Monitoring.Files = []core.File{{Path: fixture, Alias: "synthetic", HashOnly: true}}
	for path, data := range map[string]string{c.Agent.TokenFile: "cs_" + strings.Repeat("s", 43), fixture: "synthetic configuration"} {
		if err := os.WriteFile(path, []byte(data), 0600); err != nil {
			t.Fatal(err)
		}
	}
	data, err := yaml.Marshal(c)
	if err != nil {
		t.Fatal(err)
	}
	configPath := filepath.Join(dir, "agent.yaml")
	if err := os.WriteFile(configPath, data, 0600); err != nil {
		t.Fatal(err)
	}
	previousFlags, previousArgs := flag.CommandLine, os.Args
	t.Cleanup(func() { flag.CommandLine = previousFlags; os.Args = previousArgs })
	cycle := func() error {
		flag.CommandLine = flag.NewFlagSet("review-agent", flag.ContinueOnError)
		os.Args = []string{"review-agent", "--config", configPath, "--once"}
		return run()
	}
	if err := cycle(); err == nil {
		t.Fatal("expected ingestion failure")
	}
	if heartbeats.Load() != 0 {
		t.Fatal("known heartbeat suppression changed; update readiness decision")
	}
	failed.Store(false)
	if err := cycle(); err != nil {
		t.Fatal("recovery cycle failed")
	}
	if heartbeats.Load() != 1 {
		t.Fatal("heartbeat did not recover after queued batch delivery")
	}
	t.Log("KNOWN GAP: real runner suppresses heartbeat on failed ingestion; recovery sends preserved batch and heartbeat")
}
