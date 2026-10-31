package core

import (
	"context"
	"github.com/google/uuid"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestFlushWorkerDoesNotBlockHeartbeatAndCancels(t *testing.T) {
	entered := make(chan struct{})
	release := make(chan struct{})
	central := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/agent/events:batch" {
			close(entered)
			select {
			case <-r.Context().Done():
			case <-release:
			}
			return
		}
		w.WriteHeader(202)
		_, _ = w.Write([]byte(`{"ok":true,"server_time":"2026-10-31T00:00:00Z","clock_skew_warning":false}`))
	}))
	defer central.Close()
	defer close(release)
	dir := t.TempDir()
	token := filepath.Join(dir, "agent.token")
	if err := os.WriteFile(token, []byte("cs_"+strings.Repeat("s", 43)), 0600); err != nil {
		t.Fatal(err)
	}
	q, err := OpenQueue(filepath.Join(dir, "queue.sqlite"), uuid.NewString(), 1)
	if err != nil {
		t.Fatal(err)
	}
	defer q.DB.Close()
	if err = q.Observe("synthetic", Snapshot{State: "present", Hash: strings.Repeat("a", 64), Ever: true}, time.Now().UTC()); err != nil {
		t.Fatal(err)
	}
	var c Config
	c.Agent.URL = central.URL
	c.Agent.TokenFile = token
	c.Agent.Batch = 100
	transport := NewTransport(c)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	wake := make(chan struct{}, 1)
	done := make(chan struct{})
	go func() { defer close(done); transport.RunFlush(ctx, q, wake) }()
	wake <- struct{}{}
	select {
	case <-entered:
	case <-time.After(3 * time.Second):
		t.Fatal("flush did not start")
	}
	hbctx, hbcancel := context.WithTimeout(ctx, time.Second)
	defer hbcancel()
	if err = transport.Heartbeat(hbctx, q, time.Now().UTC()); err != nil {
		t.Fatal("heartbeat blocked by in-flight ingestion")
	}
	cancel()
	select {
	case <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("worker did not cancel")
	}
	depth, err := q.Depth()
	if err != nil || depth != 1 {
		t.Fatal("cancellation lost pending event")
	}
}
