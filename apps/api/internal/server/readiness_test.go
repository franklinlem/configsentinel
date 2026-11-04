package server

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Review fixtures use their own schema; this never connects to the deployed DB.
func reviewServer(t *testing.T, tracer pgx.QueryTracer) (*Server, string, string, string) {
	t.Helper()
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("isolated TEST_DATABASE_URL required")
	}
	ctx := context.Background()
	root, e := pgxpool.New(ctx, dsn)
	if e != nil {
		t.Fatal(e)
	}
	schema := "review_" + strings.ReplaceAll(id(), "-", "")
	if _, e = root.Exec(ctx, "CREATE SCHEMA "+schema); e != nil {
		root.Close()
		t.Fatal(e)
	}
	cfg, e := pgxpool.ParseConfig(dsn)
	if e != nil {
		t.Fatal(e)
	}
	cfg.ConnConfig.RuntimeParams["search_path"] = schema
	cfg.ConnConfig.Tracer = tracer
	cfg.MaxConns = 10
	db, e := pgxpool.NewWithConfig(ctx, cfg)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { db.Close(); _, _ = root.Exec(ctx, "DROP SCHEMA "+schema+" CASCADE"); root.Close() })
	sql, e := os.ReadFile("../../../../db/migrations/001_initial.sql")
	if e != nil {
		t.Fatal(e)
	}
	app := New(db, "https://review.example", true)
	if e = app.Migrate(ctx, string(sql)); e != nil {
		t.Fatal(e)
	}
	next, e := os.ReadFile("../../../../db/migrations/002_queue_capacity.sql")
	if e != nil {
		t.Fatal(e)
	}
	if e = app.MigrateNext(ctx, 2, string(next)); e != nil {
		t.Fatal(e)
	}
	if e = app.MigrateNext(ctx, 2, string(next)); e != nil {
		t.Fatal("migration must be idempotent", e)
	}

	if e = app.Bootstrap(ctx, "review@example.test", "synthetic-review-password"); e != nil {
		t.Fatal(e)
	}
	var uid, org, env string
	if e = db.QueryRow(ctx, "SELECT u.id,m.organization_id FROM users u JOIN memberships m ON m.user_id=u.id LIMIT 1").Scan(&uid, &org); e != nil {
		t.Fatal(e)
	}
	if e = db.QueryRow(ctx, "SELECT id FROM environments LIMIT 1").Scan(&env); e != nil {
		t.Fatal(e)
	}
	sid, aid := id(), id()
	if _, e = db.Exec(ctx, "INSERT INTO servers(id,environment_id,display_name) VALUES($1,$2,'synthetic-review')", sid, env); e != nil {
		t.Fatal(e)
	}
	if _, e = db.Exec(ctx, "INSERT INTO agents(id,server_id,installation_id) VALUES($1,$2,$3)", aid, sid, id()); e != nil {
		t.Fatal(e)
	}
	_ = uid
	return app, org, sid, aid
}
func reviewRequest(h http.Handler, method, path string, body any, token string, cookie *http.Cookie, csrf string) *httptest.ResponseRecorder {
	var input io.Reader
	if body != nil {
		data, _ := json.Marshal(body)
		input = bytes.NewReader(data)
	}
	r := httptest.NewRequest(method, "https://review.example/api/v1"+path, input)
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Origin", "https://review.example")
	r.Header.Set("X-CSRF-Token", csrf)
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	if cookie != nil {
		r.AddCookie(cookie)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}
func reviewLogin(t *testing.T, app *Server) (*http.Cookie, string) {
	t.Helper()
	w := reviewRequest(app.Routes(), "POST", "/auth/login", map[string]string{"email": "review@example.test", "password": "synthetic-review-password"}, "", nil, "")
	if w.Code != 200 {
		t.Fatal("review login failed")
	}
	var result map[string]string
	if json.Unmarshal(w.Body.Bytes(), &result) != nil {
		t.Fatal("invalid response")
	}
	return w.Result().Cookies()[0], result["csrf_token"]
}
func TestReadinessTokenAndSessionBoundaries(t *testing.T) {
	app, _, sid, aid := reviewServer(t, nil)
	if app.CheckRuntime(context.Background()) == nil {
		t.Fatal("administrative database role accepted for runtime")
	}
	h := app.Routes()
	cookie, csrf := reviewLogin(t, app)
	if !cookie.Secure || !cookie.HttpOnly || cookie.SameSite != http.SameSiteStrictMode || cookie.MaxAge != 28800 || cookie.Domain != "" {
		t.Fatal("cookie protections absent")
	}
	prior := slog.Default()
	var logs bytes.Buffer
	slog.SetDefault(slog.New(slog.NewJSONHandler(&logs, nil)))
	defer slog.SetDefault(prior)
	issued := reviewRequest(h, "POST", "/agents/"+aid+"/tokens", nil, "", cookie, csrf)
	if issued.Code != 201 {
		t.Fatal("token issue failed")
	}
	var cred map[string]string
	if json.Unmarshal(issued.Body.Bytes(), &cred) != nil {
		t.Fatal("invalid credential response")
	}
	token := cred["token"]
	if len(token) != 46 || issued.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("token exposure controls absent")
	}
	listed := reviewRequest(h, "GET", "/agents/"+aid+"/tokens", nil, "", cookie, csrf)
	if listed.Code != 200 || strings.Contains(listed.Body.String(), token) {
		t.Fatal("token returned a second time")
	}
	var stored string
	if e := app.DB.QueryRow(context.Background(), "SELECT secret_hash FROM agent_tokens WHERE id=$1", cred["token_id"]).Scan(&stored); e != nil || stored != digest(token) {
		t.Fatal("token not stored as SHA256")
	}
	var persisted string
	_ = app.DB.QueryRow(context.Background(), "SELECT coalesce(string_agg(data_redacted::text,''),'') FROM audit_logs").Scan(&persisted)
	if strings.Contains(persisted, token) || strings.Contains(logs.String(), token) {
		t.Fatal("raw token persisted in audit or logs")
	}
	if reviewRequest(h, "GET", "/servers/"+sid, nil, token, nil, "").Code != 401 {
		t.Fatal("agent token accessed admin API")
	}
	if reviewRequest(h, "POST", "/agent/heartbeat", map[string]any{"agent_id": id(), "agent_version": "0.1.0", "queue_depth": 0, "observed_at": time.Now().UTC()}, token, nil, "").Code != 422 {
		t.Fatal("identity injection accepted")
	}
	heartbeat := map[string]any{"agent_version": "0.1.0", "queue_depth": 0, "observed_at": time.Now().UTC()}
	if reviewRequest(h, "POST", "/agent/heartbeat", heartbeat, "", cookie, csrf).Code != 401 {
		t.Fatal("admin cookie authorized agent ingestion")
	}
	_, _ = app.DB.Exec(context.Background(), "UPDATE agent_tokens SET expires_at=now()-interval '1 second' WHERE id=$1", cred["token_id"])
	if reviewRequest(h, "POST", "/agent/heartbeat", heartbeat, token, nil, "").Code != 401 {
		t.Fatal("expired token accepted")
	}
	if reviewRequest(h, "POST", "/agents/"+aid+"/tokens", nil, "", cookie, "bad-csrf").Code != 403 {
		t.Fatal("invalid CSRF accepted")
	}
	if e := app.ResetPassword(context.Background(), "review@example.test", "new-synthetic-review-password"); e != nil {
		t.Fatal(e)
	}
	if reviewRequest(h, "GET", "/me", nil, "", cookie, csrf).Code != 401 {
		t.Fatal("reset did not revoke existing sessions")
	}
	t.Log("one-time token, hashed persistence, redacted audit/logs, agent/admin separation, expiry, CSRF and reset revocation verified")
}
func TestReadinessAlertCharacterization(t *testing.T) {
	app, _, _, aid := reviewServer(t, nil)
	cookie, csrf := reviewLogin(t, app)
	ctx := context.Background()
	cases := []struct {
		name           string
		seen, observed time.Duration
		queue          int
		want           []string
	}{{"healthy", 0, 0, 0, nil}, {"offline", 6 * time.Minute, 0, 0, []string{"agent_offline"}}, {"delayed", 0, 6 * time.Minute, 0, []string{"collection_delayed"}}, {"queue", 0, 0, 8000, []string{"queue_high"}}, {"offline_plus_queue", 6 * time.Minute, 0, 8000, []string{"agent_offline", "queue_high"}}}
	// Existing agents omit queue_capacity and keep the previous 8000 threshold.
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			now := time.Now().UTC()
			_, e := app.DB.Exec(ctx, "UPDATE agents SET last_seen_at=$2,last_observed_at=$3,queue_depth=$4,clock_skew_warning=false WHERE id=$1", aid, now.Add(-tc.seen), now.Add(-tc.observed), tc.queue)
			if e != nil {
				t.Fatal(e)
			}
			w := reviewRequest(app.Routes(), "GET", "/alerts", nil, "", cookie, csrf)
			if w.Code != 200 {
				t.Fatal("alerts unavailable")
			}
			var result struct {
				Items []struct {
					Kind string `json:"kind"`
				}
			}
			if json.Unmarshal(w.Body.Bytes(), &result) != nil {
				t.Fatal("invalid alerts")
			}
			if len(result.Items) != len(tc.want) {
				t.Fatalf("unexpected alert count for %s: got %d, want %d", tc.name, len(result.Items), len(tc.want))
			}
			for _, want := range tc.want {
				found := false
				for _, item := range result.Items {
					if item.Kind == want {
						found = true
					}
				}
				if !found {
					t.Fatalf("missing alert %s for %s", want, tc.name)
				}
			}
		})
	}
	for _, tc := range []struct {
		capacity, depth int
		want            bool
	}{{10, 7, false}, {10, 8, true}, {3, 2, false}, {3, 3, true}, {1, 1, true}, {10, 12, true}} {
		if _, err := app.DB.Exec(ctx, "UPDATE agents SET last_seen_at=now(),last_observed_at=now(),queue_depth=$2,queue_capacity=$3 WHERE id=$1", aid, tc.depth, tc.capacity); err != nil {
			t.Fatal(err)
		}
		w := reviewRequest(app.Routes(), "GET", "/alerts", nil, "", cookie, csrf)
		var result struct {
			Items []struct {
				Kind string `json:"kind"`
			} `json:"items"`
		}
		if w.Code != 200 || json.Unmarshal(w.Body.Bytes(), &result) != nil {
			t.Fatal("alerts unavailable")
		}
		found := false
		for _, item := range result.Items {
			if item.Kind == "queue_high" {
				found = true
			}
		}
		if found != tc.want {
			t.Fatalf("capacity %d depth %d: alert %v", tc.capacity, tc.depth, found)
		}
	}
}

type reviewTrace struct {
	mu         sync.Mutex
	statements int
	duration   time.Duration
}

func (tr *reviewTrace) TraceQueryStart(ctx context.Context, _ *pgx.Conn, _ pgx.TraceQueryStartData) context.Context {
	return context.WithValue(ctx, reviewTraceKey{}, time.Now())
}

type reviewTraceKey struct{}

func (tr *reviewTrace) TraceQueryEnd(ctx context.Context, _ *pgx.Conn, _ pgx.TraceQueryEndData) {
	start, _ := ctx.Value(reviewTraceKey{}).(time.Time)
	tr.mu.Lock()
	tr.statements++
	tr.duration += time.Since(start)
	tr.mu.Unlock()
}
func TestReadinessIngestionQueryCost(t *testing.T) {
	tr := &reviewTrace{}
	app, _, _, aid := reviewServer(t, tr)
	cookie, csrf := reviewLogin(t, app)
	issued := reviewRequest(app.Routes(), "POST", "/agents/"+aid+"/tokens", nil, "", cookie, csrf)
	var cred map[string]string
	_ = json.Unmarshal(issued.Body.Bytes(), &cred)
	events := []Event{}
	for i := 0; i < 100; i++ {
		events = append(events, Event{UUID: id(), Sequence: int64(i + 1), Alias: "synthetic-file", Kind: "baseline", New: strings.Repeat("a", 64), Observed: time.Now().UTC()})
	}
	tr.mu.Lock()
	tr.statements = 0
	tr.duration = 0
	tr.mu.Unlock()
	start := time.Now()
	w := reviewRequest(app.Routes(), "POST", "/agent/events:batch", map[string]any{"batch_id": id(), "schema_version": 1, "events": events}, cred["token"], nil, "")
	if w.Code != 202 {
		t.Fatal("batch failed")
	}
	tr.mu.Lock()
	defer tr.mu.Unlock()
	t.Logf("100 events: traced PostgreSQL statements=%d cumulative_query_ms=%.2f handler_ms=%.2f (no race timing is a performance SLO)", tr.statements, float64(tr.duration.Microseconds())/1000, float64(time.Since(start).Microseconds())/1000)
	if tr.statements < 300 {
		t.Fatal("baseline query shape changed; re-evaluate investigation")
	}
}
