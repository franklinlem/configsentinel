package server

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

var slugRE = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{0,62}$`)
var aliasRE = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$`)

const scopeJoin = ` FROM servers s JOIN environments en ON en.id=s.environment_id JOIN projects pr ON pr.id=en.project_id JOIN memberships m ON m.organization_id=pr.organization_id `
const scopeWhere = ` m.user_id=$1 AND (m.project_id IS NULL OR m.project_id=pr.id) `

func (s *Server) access(w http.ResponseWriter, r *http.Request, kind, key, level string) (string, bool) {
	if !validID(key) {
		problem(w, 404, "Recurso não encontrado")
		return "", false
	}
	var q string
	switch kind {
	case "organization":
		q = `SELECT m.organization_id,m.role FROM memberships m WHERE m.user_id=$1 AND m.organization_id=$2`
	case "project":
		q = `SELECT pr.organization_id,m.role FROM projects pr JOIN memberships m ON m.organization_id=pr.organization_id WHERE m.user_id=$1 AND pr.id=$2 AND (m.project_id IS NULL OR m.project_id=pr.id)`
	case "environment":
		q = `SELECT pr.organization_id,m.role FROM environments en JOIN projects pr ON pr.id=en.project_id JOIN memberships m ON m.organization_id=pr.organization_id WHERE m.user_id=$1 AND en.id=$2 AND (m.project_id IS NULL OR m.project_id=pr.id)`
	case "server":
		q = `SELECT pr.organization_id,m.role` + scopeJoin + `WHERE` + scopeWhere + `AND s.id=$2`
	case "agent":
		q = `SELECT pr.organization_id,m.role` + scopeJoin + `JOIN agents a ON a.server_id=s.id WHERE` + scopeWhere + `AND a.id=$2`
	case "event":
		q = `SELECT pr.organization_id,m.role` + scopeJoin + `JOIN agents a ON a.server_id=s.id JOIN change_events ev ON ev.agent_id=a.id WHERE` + scopeWhere + `AND ev.id=$2`
	default:
		panic("invalid scope")
	}
	var org, role string
	if s.DB.QueryRow(r.Context(), q, p(r).User, key).Scan(&org, &role) != nil {
		problem(w, 404, "Recurso não encontrado")
		return "", false
	}
	allowed := level == "read" || role == "owner" || (level == "manage" && role == "admin") || (level == "ack" && (role == "admin" || role == "analyst"))
	if !allowed {
		problem(w, 403, "Permissão insuficiente")
		return "", false
	}
	return org, true
}
func (s *Server) auditTx(r *http.Request, tx pgx.Tx, org, op, kind, target string) error {
	_, e := tx.Exec(r.Context(), `INSERT INTO audit_logs(id,organization_id,actor_id,operation,target_type,target_id) VALUES($1,$2,$3,$4,$5,$6)`, id(), org, p(r).User, op, kind, target)
	return e
}
func (s *Server) mutation(w http.ResponseWriter, r *http.Request, org, op, kind, target, q string, args ...any) bool {
	tx, e := s.DB.Begin(r.Context())
	if e != nil {
		problem(w, 503, "Banco indisponível")
		return false
	}
	defer tx.Rollback(r.Context())
	if _, e = tx.Exec(r.Context(), q, args...); e != nil {
		problem(w, 409, "Cadastro conflita com registro existente ou vínculo inválido")
		return false
	}
	if e = s.auditTx(r, tx, org, op, kind, target); e != nil {
		problem(w, 503, "Auditoria indisponível")
		return false
	}
	if tx.Commit(r.Context()) != nil {
		problem(w, 503, "Gravação indisponível")
		return false
	}
	return true
}
func (s *Server) organizations(w http.ResponseWriter, r *http.Request) {
	s.rows(w, r, `SELECT o.*,m.role,m.project_id FROM organizations o JOIN memberships m ON m.organization_id=o.id WHERE m.user_id=$1 ORDER BY o.name LIMIT 100`, p(r).User)
}
func (s *Server) createOrganization(w http.ResponseWriter, r *http.Request) {
	var b struct {
		Name string `json:"name"`
		Slug string `json:"slug"`
	}
	if !decode(w, r, &b) {
		return
	}
	if !slugRE.MatchString(b.Slug) || len(strings.TrimSpace(b.Name)) == 0 || len(b.Name) > 120 {
		problem(w, 422, "Nome ou slug inválido")
		return
	}
	var owner bool
	_ = s.DB.QueryRow(r.Context(), `SELECT EXISTS(SELECT 1 FROM memberships WHERE user_id=$1 AND role='owner')`, p(r).User).Scan(&owner)
	if !owner {
		problem(w, 403, "Somente owner pode criar organização")
		return
	}
	org := id()
	tx, e := s.DB.Begin(r.Context())
	if e != nil {
		problem(w, 503, "Banco indisponível")
		return
	}
	defer tx.Rollback(r.Context())
	if _, e = tx.Exec(r.Context(), `INSERT INTO organizations(id,slug,name) VALUES($1,$2,$3)`, org, b.Slug, b.Name); e == nil {
		_, e = tx.Exec(r.Context(), `INSERT INTO memberships VALUES($1,$2,'owner',NULL)`, org, p(r).User)
	}
	if e == nil {
		e = s.auditTx(r, tx, org, "organization.created", "organization", org)
	}
	if e != nil {
		problem(w, 409, "Não foi possível criar organização")
		return
	}
	if tx.Commit(r.Context()) != nil {
		problem(w, 503, "Gravação indisponível")
		return
	}
	write(w, 201, map[string]string{"id": org})
}
func (s *Server) projects(w http.ResponseWriter, r *http.Request) {
	org := chi.URLParam(r, "orgId")
	if _, ok := s.access(w, r, "organization", org, "read"); !ok {
		return
	}
	s.rows(w, r, `SELECT pr.* FROM projects pr JOIN memberships m ON m.organization_id=pr.organization_id WHERE m.user_id=$1 AND pr.organization_id=$2 AND (m.project_id IS NULL OR m.project_id=pr.id) ORDER BY pr.name LIMIT 100`, p(r).User, org)
}
func (s *Server) environments(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "projectId")
	if _, ok := s.access(w, r, "project", key, "read"); !ok {
		return
	}
	s.rows(w, r, `SELECT * FROM environments WHERE project_id=$1 ORDER BY name LIMIT 100`, key)
}
func (s *Server) createProject(w http.ResponseWriter, r *http.Request) {
	s.createNamed(w, r, "organization", "orgId", "owner", `INSERT INTO projects VALUES($1,$2,$3,$4)`, "project")
}
func (s *Server) createEnvironment(w http.ResponseWriter, r *http.Request) {
	s.createNamed(w, r, "project", "projectId", "manage", `INSERT INTO environments VALUES($1,$2,$3,$4)`, "environment")
}
func (s *Server) createNamed(w http.ResponseWriter, r *http.Request, parent, param, level, q, kind string) {
	key := chi.URLParam(r, param)
	org, ok := s.access(w, r, parent, key, level)
	if !ok {
		return
	}
	var b struct {
		Name string `json:"name"`
		Slug string `json:"slug"`
	}
	if !decode(w, r, &b) {
		return
	}
	if !slugRE.MatchString(b.Slug) || len(strings.TrimSpace(b.Name)) == 0 || len(b.Name) > 120 {
		problem(w, 422, "Nome ou slug inválido")
		return
	}
	target := id()
	if s.mutation(w, r, org, kind+".created", kind, target, q, target, key, b.Slug, b.Name) {
		write(w, 201, map[string]string{"id": target})
	}
}

const serverColumns = `SELECT s.id,s.display_name,s.environment_id,en.name environment,pr.name project,pr.id project_id,pr.organization_id,a.id agent_id,a.last_seen_at,a.last_observed_at,a.agent_version,a.queue_depth,a.clock_skew_warning,CASE WHEN a.id IS NULL THEN 'not_installed' WHEN a.last_seen_at IS NULL OR a.last_seen_at<now()-interval '5 minutes' THEN 'offline' WHEN a.last_observed_at IS NULL OR a.last_observed_at<now()-interval '5 minutes' THEN 'delayed' ELSE 'online' END status`
const serverAgentJoin = ` LEFT JOIN LATERAL (SELECT * FROM agents ag WHERE ag.server_id=s.id AND ag.revoked_at IS NULL ORDER BY ag.last_seen_at DESC NULLS LAST,ag.id LIMIT 1) a ON true `

func (s *Server) allServers(w http.ResponseWriter, r *http.Request) {
	s.rows(w, r, serverColumns+scopeJoin+serverAgentJoin+`WHERE`+scopeWhere+`ORDER BY s.display_name,s.id LIMIT 200`, p(r).User)
}
func (s *Server) servers(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "envId")
	if _, ok := s.access(w, r, "environment", key, "read"); !ok {
		return
	}
	s.rows(w, r, serverColumns+scopeJoin+serverAgentJoin+`WHERE`+scopeWhere+`AND en.id=$2 ORDER BY s.display_name LIMIT 200`, p(r).User, key)
}
func (s *Server) serverDetail(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "serverId")
	if _, ok := s.access(w, r, "server", key, "read"); !ok {
		return
	}
	s.rows(w, r, serverColumns+scopeJoin+serverAgentJoin+`WHERE`+scopeWhere+`AND s.id=$2`, p(r).User, key)
}
func (s *Server) createServer(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "envId")
	org, ok := s.access(w, r, "environment", key, "manage")
	if !ok {
		return
	}
	var b struct {
		Name string `json:"display_name"`
	}
	if !decode(w, r, &b) {
		return
	}
	if !aliasRE.MatchString(b.Name) {
		problem(w, 422, "Nome lógico inválido (1–80 letras, números, ponto, hífen ou sublinhado)")
		return
	}
	target := id()
	if s.mutation(w, r, org, "server.created", "server", target, `INSERT INTO servers(id,environment_id,display_name) VALUES($1,$2,$3)`, target, key, b.Name) {
		write(w, 201, map[string]string{"id": target})
	}
}
func (s *Server) provision(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "serverId")
	org, ok := s.access(w, r, "server", key, "manage")
	if !ok {
		return
	}
	agent, tid, token := id(), id(), "cs_"+secret()
	tx, e := s.DB.Begin(r.Context())
	if e != nil {
		problem(w, 503, "Banco indisponível")
		return
	}
	defer tx.Rollback(r.Context())
	_, e = tx.Exec(r.Context(), `INSERT INTO agents(id,server_id,installation_id) VALUES($1,$2,$3)`, agent, key, id())
	if e == nil {
		_, e = tx.Exec(r.Context(), `INSERT INTO agent_tokens(id,agent_id,prefix,secret_hash) VALUES($1,$2,$3,$4)`, tid, agent, token[:11], digest(token))
	}
	if e == nil {
		e = s.auditTx(r, tx, org, "agent.provisioned", "agent", agent)
	}
	if e != nil || tx.Commit(r.Context()) != nil {
		problem(w, 503, "Provisionamento indisponível")
		return
	}
	write(w, 201, map[string]string{"agent_id": agent, "token_id": tid, "token": token})
}
func (s *Server) tokens(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "agentId")
	if _, ok := s.access(w, r, "agent", key, "manage"); !ok {
		return
	}
	s.rows(w, r, `SELECT id,prefix,created_at,expires_at,revoked_at FROM agent_tokens WHERE agent_id=$1 ORDER BY created_at DESC LIMIT 100`, key)
}
func (s *Server) rotate(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "agentId")
	org, ok := s.access(w, r, "agent", key, "manage")
	if !ok {
		return
	}
	tid, token := id(), "cs_"+secret()
	if s.mutation(w, r, org, "token.issued", "agent", key, `INSERT INTO agent_tokens(id,agent_id,prefix,secret_hash) VALUES($1,$2,$3,$4)`, tid, key, token[:11], digest(token)) {
		write(w, 201, map[string]string{"agent_id": key, "token_id": tid, "token": token})
	}
}
func (s *Server) revoke(w http.ResponseWriter, r *http.Request) {
	key, tid := chi.URLParam(r, "agentId"), chi.URLParam(r, "tokenId")
	org, ok := s.access(w, r, "agent", key, "manage")
	if !ok {
		return
	}
	if !validID(tid) {
		problem(w, 404, "Credencial não encontrada")
		return
	}
	var exists bool
	_ = s.DB.QueryRow(r.Context(), `SELECT EXISTS(SELECT 1 FROM agent_tokens WHERE id=$1 AND agent_id=$2)`, tid, key).Scan(&exists)
	if !exists {
		problem(w, 404, "Credencial não encontrada")
		return
	}
	if s.mutation(w, r, org, "token.revoked", "token", tid, `UPDATE agent_tokens SET revoked_at=now() WHERE id=$1 AND agent_id=$2`, tid, key) {
		write(w, 200, map[string]bool{"ok": true})
	}
}
func (s *Server) observations(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "serverId")
	if _, ok := s.access(w, r, "server", key, "read"); !ok {
		return
	}
	s.rows(w, r, `SELECT f.* FROM file_observations f JOIN agents a ON a.id=f.agent_id WHERE a.server_id=$1 ORDER BY f.file_alias LIMIT 1000`, key)
}

type cursor struct {
	Time time.Time `json:"time"`
	ID   string    `json:"id"`
}

func (s *Server) events(w http.ResponseWriter, r *http.Request) {
	limit := 50
	if v, e := strconv.Atoi(r.URL.Query().Get("limit")); e == nil && v > 0 && v <= 100 {
		limit = v
	}
	args := []any{p(r).User}
	where := scopeWhere
	add := func(clause string, v any) {
		args = append(args, v)
		where += " AND " + strings.ReplaceAll(clause, "?", "$"+strconv.Itoa(len(args)))
	}
	for _, f := range []struct{ key, col string }{{"server_id", "s.id"}, {"environment_id", "en.id"}} {
		if v := r.URL.Query().Get(f.key); v != "" {
			if !validID(v) {
				problem(w, 422, "Filtro inválido")
				return
			}
			add(f.col+"=?", v)
		}
	}
	if k := r.URL.Query().Get("kind"); k != "" {
		add("ev.kind=?", k)
	}
	if q := r.URL.Query().Get("q"); q != "" {
		if len(q) > 80 {
			problem(w, 422, "Busca longa demais")
			return
		}
		add("ev.file_alias ILIKE ?", "%"+q+"%")
	}
	for _, f := range []struct{ key, op string }{{"from", ">="}, {"to", "<="}} {
		if v := r.URL.Query().Get(f.key); v != "" {
			t, e := time.Parse(time.RFC3339, v)
			if e != nil {
				problem(w, 422, "Data inválida")
				return
			}
			add("ev.received_at"+f.op+"?", t)
		}
	}
	if raw := r.URL.Query().Get("cursor"); raw != "" {
		b, e := base64.RawURLEncoding.DecodeString(raw)
		var c cursor
		if e != nil || json.Unmarshal(b, &c) != nil || !validID(c.ID) {
			problem(w, 422, "Cursor inválido")
			return
		}
		args = append(args, c.Time, c.ID)
		where += " AND (ev.received_at,ev.id)<($" + strconv.Itoa(len(args)-1) + ",$" + strconv.Itoa(len(args)) + ")"
	}
	args = append(args, limit+1)
	q := `SELECT ev.*,s.display_name server_name,s.id server_id,en.name environment,EXISTS(SELECT 1 FROM acknowledgements ac WHERE ac.event_id=ev.id) acknowledged` + scopeJoin + `JOIN agents a ON a.server_id=s.id JOIN change_events ev ON ev.agent_id=a.id WHERE ` + where + ` ORDER BY ev.received_at DESC,ev.id DESC LIMIT $` + strconv.Itoa(len(args))
	rows, e := s.DB.Query(r.Context(), q, args...)
	if e != nil {
		problem(w, 503, "Consulta indisponível")
		return
	}
	defer rows.Close()
	items := []map[string]any{}
	for rows.Next() {
		vals, e := rows.Values()
		if e != nil {
			problem(w, 503, "Consulta indisponível")
			return
		}
		m := map[string]any{}
		for i, f := range rows.FieldDescriptions() {
			if v, ok := vals[i].([16]byte); ok {
				m[f.Name] = fmtUUID(v)
			} else {
				m[f.Name] = vals[i]
			}
		}
		items = append(items, m)
	}
	if rows.Err() != nil {
		problem(w, 503, "Consulta indisponível")
		return
	}
	next := ""
	if len(items) > limit {
		items = items[:limit]
		last := items[len(items)-1]
		c := cursor{Time: last["received_at"].(time.Time), ID: last["id"].(string)}
		b, _ := json.Marshal(c)
		next = base64.RawURLEncoding.EncodeToString(b)
	}
	write(w, 200, map[string]any{"items": items, "next_cursor": next})
}
func fmtUUID(v [16]byte) string { return uuid.UUID(v).String() }
func (s *Server) eventDetail(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "eventId")
	if _, ok := s.access(w, r, "event", key, "read"); !ok {
		return
	}
	s.rows(w, r, `SELECT ev.*,(SELECT coalesce(jsonb_agg(jsonb_build_object('id',ac.id,'comment',ac.comment,'created_at',ac.created_at,'actor',u.email) ORDER BY ac.created_at),'[]') FROM acknowledgements ac JOIN users u ON u.id=ac.actor_id WHERE ac.event_id=ev.id) acknowledgements FROM change_events ev WHERE ev.id=$1`, key)
}
func (s *Server) acknowledge(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "eventId")
	org, ok := s.access(w, r, "event", key, "ack")
	if !ok {
		return
	}
	var b struct {
		Comment string `json:"comment"`
	}
	if !decode(w, r, &b) {
		return
	}
	b.Comment = strings.TrimSpace(b.Comment)
	if len(b.Comment) < 3 || len(b.Comment) > 2000 {
		problem(w, 422, "Comentário deve ter entre 3 e 2000 caracteres")
		return
	}
	target := id()
	if s.mutation(w, r, org, "event.acknowledged", "event", key, `INSERT INTO acknowledgements(id,event_id,actor_id,comment) VALUES($1,$2,$3,$4)`, target, key, p(r).User, b.Comment) {
		write(w, 201, map[string]string{"id": target})
	}
}
func (s *Server) alerts(w http.ResponseWriter, r *http.Request) {
	s.rows(w, r, `SELECT ev.id,ev.file_alias,ev.kind,ev.severity,ev.received_at,s.display_name server_name,'event' source`+scopeJoin+`JOIN agents a ON a.server_id=s.id JOIN change_events ev ON ev.agent_id=a.id WHERE`+scopeWhere+`AND ev.kind <> 'baseline' AND NOT EXISTS(SELECT 1 FROM acknowledgements ac WHERE ac.event_id=ev.id) UNION ALL SELECT a.id,'',alert.kind,'warning',a.last_seen_at,s.display_name,'agent'`+scopeJoin+`JOIN agents a ON a.server_id=s.id CROSS JOIN LATERAL (VALUES ('agent_offline',a.last_seen_at IS NULL OR a.last_seen_at<now()-interval '5 minutes'),('collection_delayed',a.last_seen_at IS NOT NULL AND a.last_seen_at>=now()-interval '5 minutes' AND (a.last_observed_at IS NULL OR a.last_observed_at<now()-interval '5 minutes')),('queue_high',a.queue_depth>=8000),('clock_skew',a.clock_skew_warning)) AS alert(kind,active) WHERE`+scopeWhere+`AND a.revoked_at IS NULL AND alert.active ORDER BY received_at DESC NULLS FIRST LIMIT 100`, p(r).User)
}
func (s *Server) auditLogs(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "orgId")
	if _, ok := s.access(w, r, "organization", key, "owner"); !ok {
		return
	}
	s.rows(w, r, `SELECT a.*,u.email actor FROM audit_logs a LEFT JOIN users u ON u.id=a.actor_id WHERE organization_id=$1 ORDER BY timestamp DESC,id DESC LIMIT 100`, key)
}
func (s *Server) members(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "orgId")
	if _, ok := s.access(w, r, "organization", key, "owner"); !ok {
		return
	}
	s.rows(w, r, `SELECT u.id,u.email,m.role,m.project_id FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.organization_id=$1 ORDER BY u.email LIMIT 100`, key)
}
func (s *Server) addMember(w http.ResponseWriter, r *http.Request) {
	key := chi.URLParam(r, "orgId")
	if _, ok := s.access(w, r, "organization", key, "owner"); !ok {
		return
	}
	var b struct {
		Email     string  `json:"email"`
		Password  string  `json:"password"`
		Role      string  `json:"role"`
		ProjectID *string `json:"project_id"`
	}
	if !decode(w, r, &b) {
		return
	}
	if !strings.Contains(b.Email, "@") || len(b.Email) > 254 || len(b.Password) < 16 || len(b.Password) > 1024 || (b.Role != "owner" && b.Role != "admin" && b.Role != "analyst" && b.Role != "viewer") || (b.Role == "admin" && (b.ProjectID == nil || !validID(*b.ProjectID))) || (b.Role != "admin" && b.ProjectID != nil) {
		problem(w, 422, "E-mail, senha, perfil ou projeto inválido")
		return
	}
	uid := id()
	tx, e := s.DB.Begin(r.Context())
	if e != nil {
		problem(w, 503, "Banco indisponível")
		return
	}
	defer tx.Rollback(r.Context())
	_, e = tx.Exec(r.Context(), `INSERT INTO users(id,email,password_hash) VALUES($1,$2,$3) ON CONFLICT(email) DO NOTHING`, uid, strings.ToLower(strings.TrimSpace(b.Email)), passwordHash(b.Password))
	if e == nil {
		e = tx.QueryRow(r.Context(), `SELECT id FROM users WHERE email=$1`, strings.ToLower(strings.TrimSpace(b.Email))).Scan(&uid)
	}
	if e == nil {
		_, e = tx.Exec(r.Context(), `INSERT INTO memberships(organization_id,user_id,role,project_id) VALUES($1,$2,$3,$4)`, key, uid, b.Role, b.ProjectID)
	}
	if e == nil {
		e = s.auditTx(r, tx, key, "member.added", "user", uid)
	}
	if e != nil {
		problem(w, 409, "Membro existente ou projeto inválido")
		return
	}
	if tx.Commit(r.Context()) != nil {
		problem(w, 503, "Gravação indisponível")
		return
	}
	write(w, 201, map[string]string{"id": uid})
}
