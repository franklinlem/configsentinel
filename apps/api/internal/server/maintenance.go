package server

import (
	"context"
	"log/slog"
	"time"
)

// Retain removes expired sessions. Events, acknowledgements and administrative
// audits are preserved until an explicit data-retention policy is approved.
func (s *Server) Retain(ctx context.Context) error {
	_, e := s.DB.Exec(ctx, `DELETE FROM user_sessions WHERE expires_at<now()-interval '1 day' OR revoked_at<now()-interval '1 day'`)
	return e
}
func (s *Server) Maintenance(ctx context.Context) {
	maintenanceLoop(ctx, time.Hour, s.Retain)
}

func maintenanceLoop(ctx context.Context, interval time.Duration, retain func(context.Context) error) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		if ctx.Err() != nil {
			return
		}
		if e := retain(ctx); e != nil && ctx.Err() == nil {
			slog.Error("retention failed; will retry on next scheduled run", "error", e)
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}
