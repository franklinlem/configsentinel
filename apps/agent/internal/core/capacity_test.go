package core

import (
	"context"
	"encoding/json"
	"github.com/google/uuid"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestHeartbeatCapacityAndLegacyFallback(t *testing.T) {
	for _, legacy := range []bool{false, true} {
		t.Run(map[bool]string{false: "capacity", true: "legacy"}[legacy], func(t *testing.T) {
			calls := 0
			central := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				calls++
				var body map[string]any
				if json.NewDecoder(r.Body).Decode(&body) != nil {
					t.Error("invalid heartbeat")
					w.WriteHeader(400)
					return
				}
				capacity, exists := body["queue_capacity"]
				if calls == 1 && (!exists || capacity != float64(3)) {
					t.Error("capacity not sent")
				}
				if legacy && calls == 1 {
					w.WriteHeader(422)
					return
				}
				if legacy && calls == 2 && exists {
					t.Error("legacy fallback contains capacity")
				}
				w.WriteHeader(202)
				_, _ = w.Write([]byte(`{"ok":true,"server_time":"2026-10-31T00:00:00Z","clock_skew_warning":false}`))
			}))
			defer central.Close()
			d := t.TempDir()
			token := filepath.Join(d, "token")
			if e := os.WriteFile(token, []byte("cs_"+strings.Repeat("s", 43)), 0600); e != nil {
				t.Fatal(e)
			}
			q, e := OpenQueue(filepath.Join(d, "queue.sqlite"), uuid.NewString(), 3)
			if e != nil {
				t.Fatal(e)
			}
			defer q.DB.Close()
			var c Config
			c.Agent.URL = central.URL
			c.Agent.TokenFile = token
			if e = NewTransport(c).Heartbeat(context.Background(), q, time.Now().UTC()); e != nil {
				t.Fatal(e)
			}
			want := 1
			if legacy {
				want = 2
			}
			if calls != want {
				t.Fatalf("got %d requests", calls)
			}
		})
	}
}
