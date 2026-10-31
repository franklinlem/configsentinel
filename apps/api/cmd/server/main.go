package main

import (
	"context"
	"flag"
	"github.com/franklinlem/configsentinel/apps/api/internal/server"
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
	db, e := pgxpool.NewWithConfig(ctx, cfg)
	if e != nil {
		return e
	}
	defer db.Close()
	migration := os.Getenv("MIGRATION_FILE")
	if migration == "" {
		migration = "/app/migrations/001_initial.sql"
	}
	sql, e := os.ReadFile(migration)
	if e != nil {
		return e
	}
	app := server.New(db, origin, secure)
	if e = app.Migrate(ctx, string(sql)); e != nil {
		return e
	}
	if *reset {
		return app.ResetPassword(ctx, os.Getenv("ADMIN_EMAIL"), os.Getenv("ADMIN_PASSWORD"))
	}
	if e = app.Bootstrap(ctx, os.Getenv("ADMIN_EMAIL"), os.Getenv("ADMIN_PASSWORD")); e != nil {
		return e
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
