package core

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestHeartbeatWorkerContinuesWithStaleObservationAndCancels(t *testing.T) {
	received := make(chan map[string]any, 4)
	central := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Error(err)
			return
		}
		received <- body
		w.WriteHeader(202)
		_, _ = w.Write([]byte(`{"ok":true,"server_time":"2026-10-31T00:00:00Z","clock_skew_warning":false}`))
	}))
	defer central.Close()
	dir := privateTestDir(t)
	token := filepath.Join(dir, "token")
	if err := os.WriteFile(token, []byte("cs_"+strings.Repeat("s", 43)), 0600); err != nil {
		t.Fatal(err)
	}
	q, err := OpenQueue(filepath.Join(dir, "queue.sqlite"), uuid.NewString(), 10)
	if err != nil {
		t.Fatal(err)
	}
	defer q.DB.Close()
	var c Config
	c.Agent.URL, c.Agent.TokenFile = central.URL, token
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	stale := time.Now().Add(-10 * time.Minute).UTC()
	go func() {
		defer close(done)
		NewTransport(c).RunHeartbeat(ctx, q, func() time.Time { return stale }, 20*time.Millisecond, nil)
	}()
	for range 2 {
		select {
		case body := <-received:
			if body["observed_at"] == nil || body["sent_at"] == nil {
				t.Fatal("heartbeat missing timestamps")
			}
		case <-time.After(time.Second):
			cancel()
			t.Fatal("heartbeat did not continue")
		}
	}
	cancel()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("heartbeat did not stop")
	}
}
