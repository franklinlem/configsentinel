package server

import (
	"context"
	"errors"
)

// Fail closed if misconfigured with the old administrative database credential.
func (s *Server) CheckRuntime(ctx context.Context) error {
	var name string
	var unsafe bool
	if err := s.DB.QueryRow(ctx, `SELECT current_user,
 rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
 OR pg_has_role(current_user,'configsentinel_owner','MEMBER')
 OR pg_has_role(current_user,'configsentinel_migrator','MEMBER')
 FROM pg_roles WHERE rolname=current_user`).Scan(&name, &unsafe); err != nil {
		return err
	}
	if unsafe || name != "configsentinel_runtime" {
		return errors.New("dedicated unprivileged runtime database role required")
	}
	var version int
	if err := s.DB.QueryRow(ctx, "SELECT max(version) FROM schema_migrations").Scan(&version); err != nil {
		return errors.New("database migration required before runtime startup")
	}
	if version != 1 && version != 2 {
		return errors.New("unsupported database schema; refusing startup")
	}
	return nil
}
