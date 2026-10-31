package server

import (
	"context"
	"errors"
	"strings"
)

// ResetPassword is an operator-only CLI action, never an unauthenticated endpoint.
func (s *Server) ResetPassword(ctx context.Context, email, password string) error {
	if len(password) < 16 || len(password) > 1024 {
		return errors.New("reset password must contain 16–1024 bytes")
	}
	tx, e := s.DB.Begin(ctx)
	if e != nil {
		return e
	}
	defer tx.Rollback(ctx)
	var uid string
	e = tx.QueryRow(ctx, `UPDATE users SET password_hash=$2 WHERE email=$1 RETURNING id`, strings.ToLower(strings.TrimSpace(email)), passwordHash(password)).Scan(&uid)
	if e != nil {
		return errors.New("account not found or database unavailable")
	}
	if _, e = tx.Exec(ctx, `UPDATE user_sessions SET revoked_at=now() WHERE user_id=$1`, uid); e != nil {
		return e
	}
	if _, e = tx.Exec(ctx, `INSERT INTO audit_logs(id,organization_id,actor_id,operation,target_type,target_id) SELECT gen_random_uuid(),organization_id,$1,'user.password_reset','user',$1 FROM memberships WHERE user_id=$1`, uid); e != nil {
		return e
	}
	return tx.Commit(ctx)
}
