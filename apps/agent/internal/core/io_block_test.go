//go:build linux

package core

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"syscall"
	"testing"
	"time"

	"github.com/google/uuid"
)

// TestIOBlockFifoRefusedWithoutBlocking verifica que arquivos especiais (como FIFOs)
// são rejeitados imediatamente como "unreadable" pelo Scan graças a O_NONBLOCK e
// verificação de S_IFREG, sem bloquear a thread do agente.
func TestIOBlockFifoRefusedWithoutBlocking(t *testing.T) {
	dir := privateTestDir(t)
	fifoPath := filepath.Join(dir, "blocked.fifo")
	if err := syscall.Mkfifo(fifoPath, 0600); err != nil {
		t.Fatal(err)
	}

	done := make(chan Snapshot, 1)
	go func() {
		done <- Scan(fifoPath, 1024)
	}()

	select {
	case snap := <-done:
		if snap.State != "unreadable" {
			t.Fatalf("expected unreadable for FIFO, got %s", snap.State)
		}
	case <-time.After(500 * time.Millisecond):
		t.Fatal("Scan blocked on FIFO I/O")
	}
}

// TestHeartbeatDecoupledDuringCollectionBlock verifica que, mesmo se a rotina de
// coleta estiver suspensa/bloqueada, o worker de heartbeat continua transmitindo
// periodicamente para a central, preservando o último observed_at válido.
func TestHeartbeatDecoupledDuringCollectionBlock(t *testing.T) {
	var heartbeatCount atomic.Int64
	var lastObserved atomic.Int64
	var lastSent atomic.Int64

	central := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/agent/heartbeat" {
			w.WriteHeader(404)
			return
		}
		var hb struct {
			Observed time.Time `json:"observed_at"`
			SentAt   time.Time `json:"sent_at"`
			Queue    int       `json:"queue_depth"`
		}
		if err := json.NewDecoder(r.Body).Decode(&hb); err != nil {
			t.Error(err)
			w.WriteHeader(400)
			return
		}
		heartbeatCount.Add(1)
		lastObserved.Store(hb.Observed.Unix())
		lastSent.Store(hb.SentAt.Unix())
		w.WriteHeader(202)
		_, _ = w.Write([]byte(`{"ok":true,"server_time":"2026-11-08T00:00:00Z","clock_skew_warning":false}`))
	}))
	defer central.Close()

	dir := privateTestDir(t)
	token := filepath.Join(dir, "token")
	if err := os.WriteFile(token, []byte("cs_"+strings.Repeat("s", 43)), 0600); err != nil {
		t.Fatal(err)
	}

	q, err := OpenQueue(filepath.Join(dir, "queue.sqlite"), uuid.NewString(), 100)
	if err != nil {
		t.Fatal(err)
	}
	defer q.DB.Close()

	var c Config
	c.Agent.URL = central.URL + "/api/v1"
	c.Agent.TokenFile = token
	c.Agent.InsecureLoopback = true

	transport := NewTransport(c)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Simula a última coleta que ocorreu há 10 minutos (bloqueio ou atraso prolongado)
	staleObservation := time.Now().Add(-10 * time.Minute).UTC()

	heartbeatDone := make(chan struct{})
	go func() {
		defer close(heartbeatDone)
		transport.RunHeartbeat(ctx, q, func() time.Time {
			return staleObservation
		}, 30*time.Millisecond, nil)
	}()

	// Aguarda pelo menos 3 heartbeats enquanto a coleta está simuladamente bloqueada
	time.Sleep(150 * time.Millisecond)
	cancel()
	<-heartbeatDone

	if count := heartbeatCount.Load(); count < 3 {
		t.Fatalf("expected >= 3 heartbeats during collection stall, got %d", count)
	}

	if obs := time.Unix(lastObserved.Load(), 0).UTC(); obs.Sub(staleObservation).Abs() > 2*time.Second {
		t.Fatalf("observed_at must remain the stale collection timestamp, got %v", obs)
	}

	if sent := time.Unix(lastSent.Load(), 0).UTC(); time.Since(sent) > 5*time.Second {
		t.Fatalf("sent_at must reflect current time, got %v", sent)
	}
}
