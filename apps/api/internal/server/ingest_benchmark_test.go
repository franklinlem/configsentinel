package server

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
	"sync"
	"testing"
	"time"
)

// Explicit opt-in: this measures a synthetic isolated PostgreSQL schema only.
func TestIngestionPerformanceSample(t *testing.T) {
	if os.Getenv("RUN_INGEST_BENCHMARK") != "1" {
		t.Skip("explicit benchmark opt-in required")
	}
	app, _, server, _ := reviewServer(t, nil)
	type fixture struct {
		token  string
		events []Event
	}
	fixtures := make([]fixture, 25)
	ctx := context.Background()
	for i := range fixtures {
		agent, token := id(), fmt.Sprintf("cs_%043d", i+1)
		if _, err := app.DB.Exec(ctx, "INSERT INTO agents(id,server_id,installation_id) VALUES($1,$2,$3)", agent, server, id()); err != nil {
			t.Fatal(err)
		}
		if _, err := app.DB.Exec(ctx, "INSERT INTO agent_tokens(id,agent_id,prefix,secret_hash) VALUES($1,$2,$3,$4)", id(), agent, token[:11], digest(token)); err != nil {
			t.Fatal(err)
		}
		fixtures[i].token = token
		for n := 0; n < 100; n++ {
			fixtures[i].events = append(fixtures[i].events, Event{UUID: id(), Sequence: int64(n + 1), Alias: fmt.Sprintf("fixture-%d", n), Kind: "baseline", New: strings.Repeat("a", 64), Observed: time.Now().UTC()})
		}
	}
	durations := make([]float64, len(fixtures))
	sem := make(chan struct{}, 5)
	var wg sync.WaitGroup
	var mu sync.Mutex
	failures := 0
	start := time.Now()
	for i := range fixtures {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			begin := time.Now()
			w := reviewRequest(app.Routes(), "POST", "/agent/events:batch", map[string]any{"batch_id": id(), "schema_version": 1, "events": fixtures[i].events}, fixtures[i].token, nil, "")
			durations[i] = float64(time.Since(begin).Microseconds()) / 1000
			if w.Code != 202 {
				mu.Lock()
				failures++
				mu.Unlock()
			}
		}(i)
	}
	wg.Wait()
	sort.Float64s(durations)
	result, _ := json.Marshal(map[string]any{"environment": "local isolated Docker PostgreSQL; in-process HTTP handler", "agents": 25, "batch_size": 100, "concurrency": 5, "events": 2500, "p50_batch_ms": durations[12], "p95_batch_ms": durations[23], "max_batch_ms": durations[24], "total_seconds": time.Since(start).Seconds(), "errors": failures})
	t.Logf("INGEST_SAMPLE %s", result)
	if failures != 0 {
		t.Fatalf("%d requests failed", failures)
	}
}
