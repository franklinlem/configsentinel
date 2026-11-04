package server

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"
)

func TestPostgresAuthorizationAndIngestion(t *testing.T) {
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("TEST_DATABASE_URL required for isolated PostgreSQL integration")
	}
	ctx := context.Background()
	root, e := pgxpool.New(ctx, dsn)
	if e != nil {
		t.Fatal(e)
	}
	defer root.Close()
	schema := "test_" + strings.ReplaceAll(uuid.NewString(), "-", "")
	if _, e = root.Exec(ctx, "CREATE SCHEMA "+schema); e != nil {
		t.Fatal(e)
	}
	defer root.Exec(ctx, "DROP SCHEMA "+schema+" CASCADE")
	cfg, e := pgxpool.ParseConfig(dsn)
	if e != nil {
		t.Fatal(e)
	}
	cfg.ConnConfig.RuntimeParams["search_path"] = schema
	db, e := pgxpool.NewWithConfig(ctx, cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer db.Close()
	sql, e := os.ReadFile("../../../../db/migrations/001_initial.sql")
	if e != nil {
		t.Fatal(e)
	}
	app := New(db, "http://localhost", false)
	if e = app.Migrate(ctx, string(sql)); e != nil {
		t.Fatal(e)
	}
	// A failed incremental migration must roll back both DDL and version.
	if e = app.MigrateNext(ctx, 2, "ALTER TABLE agents ADD COLUMN synthetic_failure integer; SELECT missing_synthetic_function();"); e == nil {
		t.Fatal("failed migration accepted")
	}
	var partial bool
	if e = db.QueryRow(ctx, "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='agents' AND column_name='synthetic_failure')").Scan(&partial); e != nil || partial {
		t.Fatal("failed migration left partial schema")
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

	if e = app.Bootstrap(ctx, "owner@example.com", "initial-password-long-enough"); e != nil {
		t.Fatal(e)
	}
	handler := app.Routes()
	var cookie *http.Cookie
	csrf := ""
	request := func(method, path string, body any, bearer string, expect int) map[string]any {
		t.Helper()
		raw := ""
		if body != nil {
			b, _ := json.Marshal(body)
			raw = string(b)
		}
		r := httptest.NewRequest(method, "http://localhost/api/v1"+path, strings.NewReader(raw))
		r.Header.Set("Content-Type", "application/json")
		r.Header.Set("Origin", "http://localhost")
		if bearer != "" {
			r.Header.Set("Authorization", "Bearer "+bearer)
		} else if cookie != nil {
			r.AddCookie(cookie)
			r.Header.Set("X-CSRF-Token", csrf)
		}
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, r)
		if w.Code != expect {
			t.Fatalf("%s %s: got %d want %d: %s", method, path, w.Code, expect, w.Body.String())
		}
		if path == "/auth/login" && w.Code == 200 {
			cookie = w.Result().Cookies()[0]
		}
		var out map[string]any
		_ = json.Unmarshal(w.Body.Bytes(), &out)
		return out
	}
	request("GET", "/events", nil, "", 401)
	login := request("POST", "/auth/login", map[string]string{"email": "owner@example.com", "password": "initial-password-long-enough"}, "", 200)
	csrf = login["csrf_token"].(string)
	orgs := request("GET", "/organizations", nil, "", 200)["items"].([]any)
	org := orgs[0].(map[string]any)["id"].(string)
	var env string
	if e = db.QueryRow(ctx, "SELECT id FROM environments LIMIT 1").Scan(&env); e != nil {
		t.Fatal(e)
	}
	server := request("POST", "/environments/"+env+"/servers", map[string]string{"display_name": "test-fixture-host"}, "", 201)["id"].(string)
	cred := request("POST", "/servers/"+server+"/agents", nil, "", 201)
	token := cred["token"].(string)
	agent := cred["agent_id"].(string)
	ev := Event{UUID: uuid.NewString(), Sequence: 1, Alias: "fixture", Kind: "baseline", New: strings.Repeat("a", 64), Observed: time.Now().UTC()}
	batch := map[string]any{"batch_id": uuid.NewString(), "schema_version": 1, "events": []Event{ev}}
	request("POST", "/agent/events:batch", batch, token, 202)
	reply := request("POST", "/agent/events:batch", batch, token, 202)
	if len(reply["duplicates"].([]any)) != 1 {
		t.Fatal("not idempotent")
	}
	ev.New = strings.Repeat("b", 64)
	batch["events"] = []Event{ev}
	request("POST", "/agent/events:batch", batch, token, 409)
	ev.Sequence = 2
	ev.UUID = uuid.NewString()
	ev.Kind = "modified"
	batch["events"] = []Event{ev}
	request("POST", "/agent/events:batch", batch, token, 202)
	request("POST", "/agent/heartbeat", map[string]any{"agent_version": "0.1.0", "queue_depth": 0, "observed_at": time.Now().UTC()}, token, 202)
	request("POST", "/agent/heartbeat", map[string]any{"agent_version": "0.1.0", "queue_depth": 9, "queue_capacity": 10, "observed_at": time.Now().UTC()}, token, 202)
	var capacity int
	if e = db.QueryRow(ctx, "SELECT queue_capacity FROM agents WHERE id=$1", agent).Scan(&capacity); e != nil || capacity != 10 {
		t.Fatal("queue capacity not persisted")
	}
	request("POST", "/agent/heartbeat", map[string]any{"agent_version": "0.1.0", "queue_depth": 0, "queue_capacity": 0, "observed_at": time.Now().UTC()}, token, 422)
	request("POST", "/agent/heartbeat", map[string]any{"agent_version": "0.1.0", "queue_depth": 0, "observed_at": time.Now().UTC()}, token, 202)
	var legacy bool
	if e = db.QueryRow(ctx, "SELECT queue_capacity IS NULL FROM agents WHERE id=$1", agent).Scan(&legacy); e != nil || !legacy {
		t.Fatal("legacy heartbeat must clear stale capacity")
	}

	request("GET", "/servers", nil, "", 200)
	request("GET", "/alerts", nil, "", 200)
	events := request("GET", "/events?limit=1", nil, "", 200)
	if events["next_cursor"] == "" {
		t.Fatal("cursor absent")
	}
	request("GET", "/events?limit=1&cursor="+events["next_cursor"].(string), nil, "", 200)
	eid := events["items"].([]any)[0].(map[string]any)["id"].(string)
	request("POST", "/events/"+eid+"/acknowledgements", map[string]string{"comment": "Investigação sintética"}, "", 201)
	request("GET", "/events/"+eid, nil, "", 200)
	// A second organization has an isolated user and server; IDs alone cannot grant access.
	uid, other, otherProject, otherEnv, otherServer := id(), id(), id(), id(), id()
	for _, v := range []struct {
		q string
		a []any
	}{{`INSERT INTO users(id,email,password_hash) VALUES($1,'viewer@example.com',$2)`, []any{uid, passwordHash("viewer-password-long-enough")}}, {`INSERT INTO organizations(id,slug,name) VALUES($1,'other','Other')`, []any{other}}, {`INSERT INTO memberships VALUES($1,$2,'viewer',NULL)`, []any{other, uid}}, {`INSERT INTO projects VALUES($1,$2,'other','Other')`, []any{otherProject, other}}, {`INSERT INTO environments VALUES($1,$2,'other','Other')`, []any{otherEnv, otherProject}}, {`INSERT INTO servers(id,environment_id,display_name) VALUES($1,$2,'other-server')`, []any{otherServer, otherEnv}}} {
		if _, e = db.Exec(ctx, v.q, v.a...); e != nil {
			t.Fatal(e)
		}
	}
	request("GET", "/servers/"+otherServer, nil, "", 404)
	ownerCookie, ownerCSRF := cookie, csrf
	cookie = nil
	login = request("POST", "/auth/login", map[string]string{"email": "viewer@example.com", "password": "viewer-password-long-enough"}, "", 200)
	csrf = login["csrf_token"].(string)
	request("GET", "/events/"+eid, nil, "", 404)
	request("GET", "/servers/"+server+"/observations", nil, "", 404)
	request("POST", "/servers/"+otherServer+"/agents", nil, "", 403)
	if n := len(request("GET", "/events", nil, "", 200)["items"].([]any)); n != 0 {
		t.Fatal("tenant event leak")
	}
	request("POST", "/auth/logout", nil, "", 200)
	request("GET", "/me", nil, "", 401)
	cookie, csrf = ownerCookie, ownerCSRF
	bad := csrf
	csrf = "wrong"
	request("POST", "/servers/"+server+"/agents", nil, "", 403)
	csrf = bad
	request("DELETE", fmt.Sprintf("/agents/%s/tokens/%s", agent, cred["token_id"]), nil, "", 200)
	request("POST", "/agent/events:batch", batch, token, 401)
	request("GET", "/organizations/"+org+"/audit-logs", nil, "", 200)
	var count int
	if e = db.QueryRow(ctx, "SELECT count(*) FROM change_events").Scan(&count); e != nil || count != 2 {
		t.Fatalf("persisted events = %d, err=%v", count, e)
	}
	// Project-scoped admins cannot cross another project in the same organization.
	var originalProject string
	if e = db.QueryRow(ctx, "SELECT project_id FROM environments WHERE id=$1", env).Scan(&originalProject); e != nil {
		t.Fatal(e)
	}
	adminID, secondProject, secondEnv, secondServer := id(), id(), id(), id()
	for _, v := range []struct {
		q string
		a []any
	}{
		{`INSERT INTO users(id,email,password_hash) VALUES($1,'project-admin@example.com',$2)`, []any{adminID, passwordHash("project-admin-password-long-enough")}},
		{`INSERT INTO memberships VALUES($1,$2,'admin',$3)`, []any{org, adminID, originalProject}},
		{`INSERT INTO projects VALUES($1,$2,'second','Second')`, []any{secondProject, org}},
		{`INSERT INTO environments VALUES($1,$2,'second','Second')`, []any{secondEnv, secondProject}},
		{`INSERT INTO servers(id,environment_id,display_name) VALUES($1,$2,'second-host')`, []any{secondServer, secondEnv}},
	} {
		if _, e = db.Exec(ctx, v.q, v.a...); e != nil {
			t.Fatal(e)
		}
	}
	cookie = nil
	login = request("POST", "/auth/login", map[string]string{"email": "project-admin@example.com", "password": "project-admin-password-long-enough"}, "", 200)
	csrf = login["csrf_token"].(string)
	request("GET", "/servers/"+server, nil, "", 200)
	request("GET", "/servers/"+secondServer, nil, "", 404)
	request("POST", "/environments/"+secondEnv+"/servers", map[string]string{"display_name": "forbidden"}, "", 404)
	request("GET", "/organizations/"+org+"/audit-logs", nil, "", 403)
	request("POST", "/organizations/"+org+"/projects", map[string]string{"name": "forbidden", "slug": "forbidden"}, "", 403)
	scoped := request("GET", "/servers", nil, "", 200)["items"].([]any)
	if len(scoped) != 1 {
		t.Fatal("project admin scope leak")
	}
	// Retention removes old events and their acknowledgements, preserving administrative audit.
	if _, e = db.Exec(ctx, `UPDATE change_events SET received_at=now()-interval '91 days'`); e != nil {
		t.Fatal(e)
	}
	if e = app.Retain(ctx); e != nil {
		t.Fatal(e)
	}
	if e = db.QueryRow(ctx, "SELECT count(*) FROM change_events").Scan(&count); e != nil || count != 0 {
		t.Fatal("retention failed")
	}
	if e = db.QueryRow(ctx, "SELECT count(*) FROM audit_logs").Scan(&count); e != nil || count == 0 {
		t.Fatal("administrative audit erased")
	}

}
