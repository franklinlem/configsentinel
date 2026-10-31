//go:build linux

package main

import (
	"encoding/json"
	"flag"
	"github.com/franklinlem/configsentinel/apps/agent/internal/core"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestReadinessRunnerHeartbeatUnderIngestionFailure(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("agent intentionally refuses root")
	}
	var status atomic.Int64
	var heartbeats atomic.Int64
	var malformed atomic.Bool
	var mu sync.Mutex
	seen := map[string]int{}
	// Every ingestion response waits until a concurrent heartbeat can complete.
	// Serial flush-before-heartbeat would deadlock until the test server timeout.
	var heartbeatDone chan struct{}
	central := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v1/agent/heartbeat" {
			var hb struct {
				Observed time.Time `json:"observed_at"`
				Queue    int       `json:"queue_depth"`
			}
			if json.NewDecoder(r.Body).Decode(&hb) != nil || hb.Observed.IsZero() {
				malformed.Store(true)
			}
			heartbeats.Add(1)
			close(heartbeatDone)
			w.WriteHeader(202)
			_, _ = w.Write([]byte(`{"ok":true,"server_time":"2026-10-31T00:00:00Z","clock_skew_warning":false}`))
			return
		}
		select {
		case <-heartbeatDone:
		case <-r.Context().Done():
			return
		}
		var batch struct {
			Events []core.Event `json:"events"`
		}
		if json.NewDecoder(r.Body).Decode(&batch) != nil {
			w.WriteHeader(422)
			return
		}
		accepted, duplicates := []string{}, []string{}
		mu.Lock()
		for _, event := range batch.Events {
			if seen[event.UUID] > 0 {
				duplicates = append(duplicates, event.UUID)
			} else {
				accepted = append(accepted, event.UUID)
			}
			// Simulate a committed batch whose ACK was lost, to verify replay identity.
			seen[event.UUID]++
		}
		mu.Unlock()
		if status.Load() != 202 {
			w.WriteHeader(int(status.Load()))
			return
		}
		w.WriteHeader(202)
		_ = json.NewEncoder(w).Encode(map[string]any{"accepted": accepted, "duplicates": duplicates, "rejected": []string{}})
	}))
	defer central.Close()
	dir := t.TempDir()
	var c core.Config
	c.Agent.URL = central.URL + "/api/v1"
	c.Agent.ID = uuid.NewString()
	c.Agent.TokenFile = filepath.Join(dir, "agent.token")
	c.Agent.QueueDB = filepath.Join(dir, "queue.sqlite")
	c.Agent.InsecureLoopback = true
	c.Agent.MaxQueue = 1
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
	if err = os.WriteFile(configPath, data, 0600); err != nil {
		t.Fatal(err)
	}
	previousFlags, previousArgs := flag.CommandLine, os.Args
	t.Cleanup(func() { flag.CommandLine = previousFlags; os.Args = previousArgs })
	cycle := func(code int64) error {
		status.Store(code)
		heartbeatDone = make(chan struct{})
		flag.CommandLine = flag.NewFlagSet("review-agent", flag.ContinueOnError)
		os.Args = []string{"review-agent", "--config", configPath, "--once"}
		return run()
	}
	for _, code := range []int64{409, 422, 503} {
		if err = cycle(code); err == nil {
			t.Fatal("expected ingestion failure")
		}
		if err = os.WriteFile(fixture, []byte("changed while queue full"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	if malformed.Load() || heartbeats.Load() != 3 {
		t.Fatal("heartbeat missing or invalid during rejected/full queue")
	}
	if err = cycle(202); err != nil {
		t.Fatal("replay recovery failed")
	}
	if err = cycle(202); err != nil {
		t.Fatal("post-saturation collection failed")
	}
	if heartbeats.Load() != 5 {
		t.Fatal("heartbeat did not continue")
	}
	mu.Lock()
	defer mu.Unlock()
	if len(seen) != 2 {
		t.Fatal("event identity changed on replay or pending change lost")
	}
	replayCount := 0
	for _, n := range seen {
		if n == 4 {
			replayCount++
		}
	}
	if replayCount != 1 {
		t.Fatal("original UUID not preserved across retries")
	}
	q, err := core.OpenQueue(c.Agent.QueueDB, c.Agent.ID, 1)
	if err != nil {
		t.Fatal(err)
	}
	defer q.DB.Close()
	depth, err := q.Depth()
	if err != nil || depth != 0 {
		t.Fatal("queue not drained")
	}
}
