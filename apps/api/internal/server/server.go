package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync/atomic"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"golang.org/x/time/rate"
)

type Server struct {
	DB           *pgxpool.Pool
	Origin       string
	Secure       bool
	loginLimit   *rate.Limiter
	ingestLimit  *rate.Limiter
	ingested     atomic.Int64
	ingestErrors atomic.Int64
	ingestNanos  atomic.Int64
	ingestCount  atomic.Int64
}
type principal struct{ User, Email, Session, Agent string }
type contextKey struct{}

func New(db *pgxpool.Pool, origin string, secure bool) *Server {
	return &Server{DB: db, Origin: strings.TrimRight(origin, "/"), Secure: secure, loginLimit: rate.NewLimiter(rate.Every(3*time.Second), 10), ingestLimit: rate.NewLimiter(50, 100)}
}
func problem(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/problem+json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{"type": "about:blank", "title": http.StatusText(status), "status": status, "detail": msg})
}
func write(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func decode(w http.ResponseWriter, r *http.Request, v any) bool {
	if !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		problem(w, 415, "Use application/json")
		return false
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	if e := d.Decode(v); e != nil {
		problem(w, 422, "JSON inválido ou campo não permitido")
		return false
	}
	if d.Decode(&struct{}{}) != io.EOF {
		problem(w, 422, "Apenas um objeto JSON é permitido")
		return false
	}
	return true
}
func id() string                  { return uuid.NewString() }
func validID(s string) bool       { _, e := uuid.Parse(s); return e == nil }
func p(r *http.Request) principal { return r.Context().Value(contextKey{}).(principal) }
func (s *Server) Routes() http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.RequestID, middleware.Recoverer, middleware.Timeout(30*time.Second))
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("X-Content-Type-Options", "nosniff")
			w.Header().Set("Cache-Control", "no-store")
			next.ServeHTTP(w, r)
		})
	})
	r.Get("/api/health/live", func(w http.ResponseWriter, r *http.Request) {
		write(w, 200, map[string]any{"status": "ok", "version": "0.1.0"})
	})
	r.Get("/api/health/ready", func(w http.ResponseWriter, r *http.Request) {
		if s.DB.Ping(r.Context()) != nil {
			problem(w, 503, "Banco indisponível")
			return
		}
		write(w, 200, map[string]string{"status": "ready"})
	})
	r.Route("/api/v1", func(r chi.Router) {
		r.Post("/auth/login", s.login)
		r.Group(func(r chi.Router) {
			r.Use(s.admin)
			r.Post("/auth/logout", s.logout)
			r.Get("/me", s.me)
			r.Get("/organizations", s.organizations)
			r.Post("/organizations", s.createOrganization)
			r.Get("/organizations/{orgId}/members", s.members)
			r.Post("/organizations/{orgId}/members", s.addMember)
			r.Get("/organizations/{orgId}/projects", s.projects)
			r.Post("/organizations/{orgId}/projects", s.createProject)
			r.Get("/projects/{projectId}/environments", s.environments)
			r.Post("/projects/{projectId}/environments", s.createEnvironment)
			r.Get("/environments/{envId}/servers", s.servers)
			r.Post("/environments/{envId}/servers", s.createServer)
			r.Get("/servers", s.allServers)
			r.Get("/servers/{serverId}", s.serverDetail)
			r.Get("/servers/{serverId}/observations", s.observations)
			r.Post("/servers/{serverId}/agents", s.provision)
			r.Get("/agents/{agentId}/tokens", s.tokens)
			r.Post("/agents/{agentId}/tokens", s.rotate)
			r.Delete("/agents/{agentId}/tokens/{tokenId}", s.revoke)
			r.Get("/events", s.events)
			r.Get("/events/{eventId}", s.eventDetail)
			r.Post("/events/{eventId}/acknowledgements", s.acknowledge)
			r.Get("/alerts", s.alerts)
			r.Get("/organizations/{orgId}/audit-logs", s.auditLogs)
		})
		r.Group(func(r chi.Router) {
			r.Use(s.agent)
			r.Post("/agent/heartbeat", s.heartbeat)
			r.Post("/agent/events:batch", s.batch)
		})
	})
	return r
}
func (s *Server) Metrics() http.Handler {
	r := http.NewServeMux()
	r.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		var offline, alerts, queue int64
		err := s.DB.QueryRow(ctx, `SELECT (SELECT count(*) FROM agents WHERE revoked_at IS NULL AND (last_seen_at IS NULL OR last_seen_at<now()-interval '5 minutes')),(SELECT count(*) FROM change_events e WHERE kind<>'baseline' AND NOT EXISTS(SELECT 1 FROM acknowledgements a WHERE a.event_id=e.id)),(SELECT coalesce(sum(queue_depth),0) FROM agents WHERE revoked_at IS NULL)`).Scan(&offline, &alerts, &queue)
		if err != nil {
			problem(w, 503, "Métricas indisponíveis")
			return
		}
		w.Header().Set("Content-Type", "text/plain; version=0.0.4")
		fmt.Fprintf(w, "# TYPE events_ingested_total counter\nevents_ingested_total %d\n# TYPE event_ingest_errors_total counter\nevent_ingest_errors_total %d\n# TYPE ingest_duration_seconds summary\ningest_duration_seconds_sum %f\ningest_duration_seconds_count %d\n# TYPE agents_offline_total gauge\nagents_offline_total %d\n# TYPE alerts_open_total gauge\nalerts_open_total %d\n# TYPE agent_queue_depth gauge\nagent_queue_depth %d\n# TYPE postgres_pool_in_use gauge\npostgres_pool_in_use %d\n", s.ingested.Load(), s.ingestErrors.Load(), float64(s.ingestNanos.Load())/1e9, s.ingestCount.Load(), offline, alerts, queue, s.DB.Stat().AcquiredConns())
	})
	return r
}
func (s *Server) admin(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		c, e := r.Cookie("cs_session")
		if e != nil {
			problem(w, 401, "Sessão necessária")
			return
		}
		var a principal
		var csrf string
		e = s.DB.QueryRow(r.Context(), `SELECT u.id,u.email,se.id,se.csrf_hash FROM user_sessions se JOIN users u ON u.id=se.user_id WHERE token_hash=$1 AND expires_at>now() AND revoked_at IS NULL AND u.disabled_at IS NULL`, digest(c.Value)).Scan(&a.User, &a.Email, &a.Session, &csrf)
		if e != nil {
			problem(w, 401, "Sessão inválida ou expirada")
			return
		}
		if r.Method != "GET" {
			if r.Header.Get("Origin") != s.Origin || digest(r.Header.Get("X-CSRF-Token")) != csrf {
				problem(w, 403, "Origem ou CSRF inválido")
				return
			}
		}
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), contextKey{}, a)))
	})
}
func (s *Server) agent(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !s.ingestLimit.Allow() {
			w.Header().Set("Retry-After", "5")
			problem(w, 429, "Limite de ingestão")
			return
		}
		h := r.Header.Get("Authorization")
		if !strings.HasPrefix(h, "Bearer ") {
			problem(w, 401, "Token necessário")
			return
		}
		var a principal
		e := s.DB.QueryRow(r.Context(), `SELECT a.id FROM agent_tokens t JOIN agents a ON a.id=t.agent_id WHERE secret_hash=$1 AND t.revoked_at IS NULL AND t.expires_at>now() AND a.revoked_at IS NULL`, digest(strings.TrimPrefix(h, "Bearer "))).Scan(&a.Agent)
		if e != nil {
			problem(w, 401, "Token inválido ou revogado")
			return
		}
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), contextKey{}, a)))
	})
}
func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	if !s.loginLimit.Allow() {
		w.Header().Set("Retry-After", "30")
		problem(w, 429, "Aguarde antes de tentar novamente")
		return
	}
	if r.Header.Get("Origin") != s.Origin {
		problem(w, 403, "Origem inválida")
		return
	}
	var b struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}
	if !decode(w, r, &b) {
		return
	}
	if len(b.Password) > 1024 || len(b.Email) > 254 {
		problem(w, 401, "Credenciais inválidas")
		return
	}
	var uid, h string
	e := s.DB.QueryRow(r.Context(), `SELECT id,password_hash FROM users WHERE email=$1 AND disabled_at IS NULL`, strings.ToLower(strings.TrimSpace(b.Email))).Scan(&uid, &h)
	if e != nil {
		h = passwordHash("dummy-password-constant-time")
	}
	ok := passwordOK(b.Password, h)
	if e != nil || !ok {
		problem(w, 401, "Credenciais inválidas")
		return
	}
	token, csrf := secret(), secret()
	_, e = s.DB.Exec(r.Context(), `INSERT INTO user_sessions(id,user_id,token_hash,csrf_hash,expires_at) VALUES($1,$2,$3,$4,now()+interval '8 hours')`, id(), uid, digest(token), digest(csrf))
	if e != nil {
		problem(w, 503, "Sessão indisponível")
		return
	}
	http.SetCookie(w, &http.Cookie{Name: "cs_session", Value: token, Path: "/", HttpOnly: true, Secure: s.Secure, SameSite: http.SameSiteStrictMode, MaxAge: 28800})
	write(w, 200, map[string]string{"csrf_token": csrf})
}
func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	_, e := s.DB.Exec(r.Context(), `UPDATE user_sessions SET revoked_at=now() WHERE id=$1`, p(r).Session)
	if e != nil {
		problem(w, 503, "Falha ao revogar sessão")
		return
	}
	http.SetCookie(w, &http.Cookie{Name: "cs_session", Value: "", Path: "/", MaxAge: -1, HttpOnly: true, Secure: s.Secure, SameSite: http.SameSiteStrictMode})
	write(w, 200, map[string]bool{"ok": true})
}
func (s *Server) me(w http.ResponseWriter, r *http.Request) {
	write(w, 200, map[string]any{"id": p(r).User, "email": p(r).Email})
}
func (s *Server) rows(w http.ResponseWriter, r *http.Request, q string, args ...any) {
	rows, e := s.DB.Query(r.Context(), q, args...)
	if e != nil {
		slog.Error("query failed", "error", e)
		problem(w, 503, "Consulta indisponível")
		return
	}
	defer rows.Close()
	out := []map[string]any{}
	for rows.Next() {
		values, e := rows.Values()
		if e != nil {
			problem(w, 503, "Consulta indisponível")
			return
		}
		m := map[string]any{}
		for i, f := range rows.FieldDescriptions() {
			if v, ok := values[i].([16]byte); ok {
				m[f.Name] = uuid.UUID(v).String()
			} else {
				m[f.Name] = values[i]
			}
		}
		out = append(out, m)
	}
	if rows.Err() != nil {
		problem(w, 503, "Consulta indisponível")
		return
	}
	write(w, 200, map[string]any{"items": out})
}
func (s *Server) Bootstrap(ctx context.Context, email, password string) error {
	var n int
	if e := s.DB.QueryRow(ctx, "SELECT count(*) FROM users").Scan(&n); e != nil {
		return e
	}
	if n > 0 {
		return nil
	}
	if len(password) < 16 || !strings.Contains(email, "@") {
		return errors.New("ADMIN_EMAIL and ADMIN_PASSWORD (16+ chars) required for first bootstrap")
	}
	tx, e := s.DB.Begin(ctx)
	if e != nil {
		return e
	}
	defer tx.Rollback(ctx)
	uid, org, pid, eid := id(), id(), id(), id()
	for _, v := range []struct {
		q string
		a []any
	}{{`INSERT INTO users VALUES($1,$2,$3,NULL)`, []any{uid, strings.ToLower(email), passwordHash(password)}}, {`INSERT INTO organizations(id,slug,name) VALUES($1,'franklin','Franklin Martins')`, []any{org}}, {`INSERT INTO projects VALUES($1,$2,'infraestrutura','Infraestrutura')`, []any{pid, org}}, {`INSERT INTO memberships VALUES($1,$2,'owner',NULL)`, []any{org, uid}}, {`INSERT INTO environments VALUES($1,$2,'homologacao','Homologação')`, []any{eid, pid}}} {
		if _, e = tx.Exec(ctx, v.q, v.a...); e != nil {
			return e
		}
	}
	return tx.Commit(ctx)
}
func (s *Server) Migrate(ctx context.Context, sql string) error {
	conn, e := s.DB.Acquire(ctx)
	if e != nil {
		return e
	}
	defer conn.Release()
	if _, e = conn.Exec(ctx, "SELECT pg_advisory_lock(72819921)"); e != nil {
		return e
	}
	defer conn.Exec(ctx, "SELECT pg_advisory_unlock(72819921)")
	var exists bool
	if e = conn.QueryRow(ctx, "SELECT to_regclass('schema_migrations') IS NOT NULL").Scan(&exists); e != nil {
		return e
	}
	if exists {
		return nil
	}
	tx, e := conn.Begin(ctx)
	if e != nil {
		return e
	}
	defer tx.Rollback(ctx)
	if _, e = tx.Exec(ctx, sql); e != nil {
		return e
	}
	return tx.Commit(ctx)
}
func Config() (string, string, bool, error) {
	origin := os.Getenv("PUBLIC_URL")
	u, e := url.Parse(origin)
	if e != nil || u.Host == "" || u.Path != "" || u.RawQuery != "" || u.Fragment != "" || u.User != nil {
		return "", "", false, errors.New("PUBLIC_URL must be an origin without path")
	}
	secure := os.Getenv("COOKIE_SECURE") != "false"
	if secure && u.Scheme != "https" {
		return "", "", false, errors.New("secure deployment requires https")
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return "", "", false, errors.New("invalid URL scheme")
	}
	return os.Getenv("DATABASE_URL"), origin, secure, nil
}
