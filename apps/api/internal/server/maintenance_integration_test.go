package server

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

func TestRetentionInIsolatedPostgres(t *testing.T) {
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("TEST_DATABASE_URL required for isolated PostgreSQL integration")
	}
	ctx := context.Background()
	root, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer root.Close()
	schema := "retention_" + strings.ReplaceAll(uuid.NewString(), "-", "")
	if _, err = root.Exec(ctx, "CREATE SCHEMA "+schema); err != nil {
		t.Fatal(err)
	}
	defer root.Exec(ctx, "DROP SCHEMA "+schema+" CASCADE")
	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		t.Fatal(err)
	}
	cfg.ConnConfig.RuntimeParams["search_path"] = schema
	db, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	_, err = db.Exec(ctx, `CREATE TABLE change_events(id integer PRIMARY KEY, received_at timestamptz NOT NULL);
CREATE TABLE acknowledgements(event_id integer REFERENCES change_events(id) ON DELETE CASCADE);
CREATE TABLE user_sessions(expires_at timestamptz NOT NULL, revoked_at timestamptz);
INSERT INTO change_events VALUES (1, now()-interval '91 days'), (2, now());
INSERT INTO acknowledgements VALUES(1), (2);
INSERT INTO user_sessions VALUES(now()-interval '2 days',NULL),(now()+interval '1 day',NULL)`)
	if err != nil {
		t.Fatal(err)
	}
	if err = (&Server{DB: db}).Retain(ctx); err != nil {
		t.Fatal(err)
	}
	var events, acks, sessions int
	if err = db.QueryRow(ctx, `SELECT (SELECT count(*) FROM change_events),(SELECT count(*) FROM acknowledgements),(SELECT count(*) FROM user_sessions)`).Scan(&events, &acks, &sessions); err != nil {
		t.Fatal(err)
	}
	if events != 2 || acks != 2 || sessions != 1 {
		t.Fatalf("unexpected counts: %d %d %d", events, acks, sessions)
	}
}
