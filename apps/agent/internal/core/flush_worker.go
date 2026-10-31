package core

import (
	"context"
	"log/slog"
	"math/rand/v2"
	"time"
)

// RunFlush owns its retry clock. A stalled/rejected batch never gates heartbeats
// or observations. Queue operations remain serialized by SQLite's connection.
func (t *Transport) RunFlush(ctx context.Context, q *Queue, wake <-chan struct{}) {
	var retry <-chan time.Time
	var timer *time.Timer
	defer func() {
		if timer != nil {
			timer.Stop()
		}
	}()
	backoff := time.Second
	for {
		select {
		case <-ctx.Done():
			return
		case <-wake:
			if retry != nil {
				continue
			}
		case <-retry:
			retry = nil
		}
		if err := t.Flush(ctx, q); err != nil {
			if ctx.Err() != nil {
				return
			}
			slog.Warn("delivery deferred", "error", err)
			timer = time.NewTimer(backoff + time.Duration(rand.Int64N(int64(backoff/2+1))))
			retry = timer.C
			backoff = min(backoff*2, 5*time.Minute)
		} else {
			backoff = time.Second
		}
	}
}
