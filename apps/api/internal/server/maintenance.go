package server

import (
	"context"
	"time"
)

// Retain runs bounded retention batches. Administrative audits have independent,
// deliberately non-destructive retention until the operator defines its policy.
func (s *Server) Retain(ctx context.Context) error {
	for {
		tag, e := s.DB.Exec(ctx, `DELETE FROM change_events WHERE id IN(SELECT id FROM change_events WHERE received_at<now()-interval '90 days' LIMIT 5000)`)
		if e != nil {
			return e
		}
		if tag.RowsAffected() < 5000 {
			break
		}
	}
	_, e := s.DB.Exec(ctx, `DELETE FROM user_sessions WHERE expires_at<now()-interval '1 day' OR revoked_at<now()-interval '1 day'`)
	return e
}
func (s *Server) Maintenance(ctx context.Context) {
	ticker := time.NewTicker(time.Hour)
	defer ticker.Stop()
	for {
		if e := s.Retain(ctx); e != nil && ctx.Err() == nil {
			return
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}
