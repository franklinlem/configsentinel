package main

import (
	"context"
	"flag"
	"fmt"
	"github.com/franklinlem/configsentinel/apps/api/internal/server"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
	if e := run(); e != nil {
		slog.Error("server stopped", "error", e)
		os.Exit(1)
	}
}
func run() error {
	migrate := flag.Bool("migrate", false, "one-shot migration and bootstrap using the migrator role")
	reset := flag.Bool("reset-password", false, "operator-only reset using ADMIN_EMAIL and ADMIN_PASSWORD")
	flag.Parse()
	dbURL, origin, secure, e := server.Config()
	if e != nil {
		return e
	}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	cfg, e := pgxpool.ParseConfig(dbURL)
	if e != nil {
		return e
	}
	cfg.MaxConns = 10
	if *migrate {
		cfg.AfterConnect = func(ctx context.Context, conn *pgx.Conn) error {
			var role string
			if err := conn.QueryRow(ctx, "SELECT session_user").Scan(&role); err != nil {
				return err
			}
			if role != "configsentinel_migrator" {
				return fmt.Errorf("migrator credential required")
			}
			_, err := conn.Exec(ctx, "SET ROLE configsentinel_owner")
			return err
		}
	}
	db, e := pgxpool.NewWithConfig(ctx, cfg)
	if e != nil {
		return e
	}
	defer db.Close()
	app := server.New(db, origin, secure)
	if *migrate {
		migration := os.Getenv("MIGRATION_FILE")
		if migration == "" {
			migration = "/app/migrations/001_initial.sql"
		}
		sql, err := os.ReadFile(migration)
		if err != nil {
			return err
		}
		if err = app.Migrate(ctx, string(sql)); err != nil {
			return err
		}
		if err = app.Bootstrap(ctx, os.Getenv("ADMIN_EMAIL"), os.Getenv("ADMIN_PASSWORD")); err != nil {
			return err
		}
		grants, err := os.ReadFile("/app/roles/runtime-grants.sql")
		if err != nil {
			return err
		}
		_, err = db.Exec(ctx, string(grants))
		return err
	}
	if e = app.CheckRuntime(ctx); e != nil {
		return e
	}
	if *reset {
		return app.ResetPassword(ctx, os.Getenv("ADMIN_EMAIL"), os.Getenv("ADMIN_PASSWORD"))
	}
	go app.Maintenance(ctx)
	httpServer := &http.Server{Addr: ":8081", Handler: app.Routes(), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 16384}
	metrics := &http.Server{Addr: ":9090", Handler: app.Metrics(), ReadHeaderTimeout: 5 * time.Second}
	errs := make(chan error, 2)
	go func() { errs <- httpServer.ListenAndServe() }()
	go func() { errs <- metrics.ListenAndServe() }()
	slog.Info("api ready", "version", "0.1.0")
	select {
	case <-ctx.Done():
	case e = <-errs:
		if e != http.ErrServerClosed {
			return e
		}
	}
	shut, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = metrics.Shutdown(shut)
	return httpServer.Shutdown(shut)
}
