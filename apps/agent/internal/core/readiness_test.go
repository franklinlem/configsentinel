//go:build linux

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

func TestReadinessTokenFileAndQueuePersistence(t *testing.T) {
	folder := t.TempDir()
	tokenPath := filepath.Join(folder, "agent.token")
	canary := "cs_" + strings.Repeat("s", 43)
	if e := os.WriteFile(tokenPath, []byte(canary), 0600); e != nil {
		t.Fatal(e)
	}
	central := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(503)
	}))
	defer central.Close()
	var c Config
	c.Agent.URL = central.URL
	c.Agent.TokenFile = tokenPath
	c.Agent.Batch = 100
	q, e := OpenQueue(filepath.Join(folder, "queue.sqlite"), uuid.NewString(), 10)
	if e != nil {
		t.Fatal(e)
	}
	defer q.DB.Close()
	if e = q.Observe("synthetic", Snapshot{State: "present", Hash: strings.Repeat("a", 64), Ever: true}, time.Now().UTC()); e != nil {
		t.Fatal(e)
	}
	transport := NewTransport(c)
	flushError := transport.Flush(context.Background(), q)
	if flushError == nil || strings.Contains(flushError.Error(), canary) {
		t.Fatal("delivery error missing or leaks token")
	}
	pending, _ := q.Pending(100)
	data, _ := json.Marshal(pending)
	if strings.Contains(string(data), canary) {
		t.Fatal("raw token persisted in queued events")
	}
	if e = os.Chmod(tokenPath, 0644); e != nil {
		t.Fatal(e)
	}
	if e = transport.Heartbeat(context.Background(), q, time.Now().UTC()); e == nil {
		t.Fatal("world-readable token accepted")
	}
}
func TestReadinessFilesystemPermissionAndConcurrentSwap(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("permission check requires unprivileged test process")
	}
	d := t.TempDir()
	p := filepath.Join(d, "watched.conf")
	canary := filepath.Join(d, "canary.conf")
	os.WriteFile(canary, []byte("synthetic-canary"), 0600)
	os.WriteFile(p, []byte("synthetic-authorized"), 0000)
	if Scan(p, 1024).State != "unreadable" {
		t.Fatal("unreadable fixture read")
	}
	os.Chmod(p, 0600)
	expected := Scan(p, 1024).Hash
	done := make(chan struct{})
	stop := make(chan struct{})
	go func() {
		defer close(done)
		for {
			select {
			case <-stop:
				return
			default:
			}
			replacement := p + ".replacement"
			_ = os.Remove(replacement)
			_ = os.Symlink(canary, replacement)
			_ = os.Rename(replacement, p)
			_ = os.WriteFile(replacement, []byte("synthetic-authorized"), 0600)
			_ = os.Rename(replacement, p)
		}
	}()
	for i := 0; i < 300; i++ {
		s := Scan(p, 1024)
		if s.Hash != "" && s.Hash != expected {
			close(stop)
			<-done
			t.Fatal("concurrent symlink target read")
		}
	}
	close(stop)
	<-done
}
