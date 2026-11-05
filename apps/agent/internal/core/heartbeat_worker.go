package core

import (
	"context"
	"log/slog"
	"time"
)

// RunHeartbeat remains independent of collection and event delivery. A zero
// observation uses the Unix epoch to represent an unknown/stale collection.
func (t *Transport) RunHeartbeat(ctx context.Context, q *Queue, observed func() time.Time, interval time.Duration, wake <-chan struct{}) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		if ctx.Err() != nil {
			return
		}
		at := observed()
		if at.IsZero() {
			at = time.Unix(0, 0).UTC()
		}
		if err := t.Heartbeat(ctx, q, at); err != nil && ctx.Err() == nil {
			slog.Warn("heartbeat deferred", "error", err)
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		case <-wake:
		}
	}
}
