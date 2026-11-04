package server

import (
	"encoding/json"
	"github.com/jackc/pgx/v5"
	"net/http"
	"regexp"
	"time"
)

type Event struct {
	UUID     string     `json:"event_uuid"`
	Sequence int64      `json:"sequence"`
	Alias    string     `json:"file_alias"`
	Kind     string     `json:"kind"`
	Old      string     `json:"old_sha256"`
	New      string     `json:"new_sha256"`
	Size     int64      `json:"file_size"`
	Mode     int64      `json:"mode"`
	Mtime    *time.Time `json:"mtime"`
	Observed time.Time  `json:"observed_at"`
}

var hashRE = regexp.MustCompile(`^[a-f0-9]{64}$`)
var kinds = map[string]bool{"baseline": true, "missing_initial": true, "created": true, "modified": true, "deleted": true, "unreadable": true, "restored": true, "recovered": true, "metadata_changed": true, "unstable": true}

func (e Event) valid() bool {
	if !validID(e.UUID) || e.Sequence < 1 || !aliasRE.MatchString(e.Alias) || !kinds[e.Kind] || e.Size < 0 || e.Size > 1<<30 || e.Mode < 0 || e.Mode > 07777 || e.Observed.IsZero() || e.Observed.After(time.Now().Add(24*time.Hour)) || e.Observed.Before(time.Date(2020, 1, 1, 0, 0, 0, 0, time.UTC)) {
		return false
	}
	if e.Old != "" && !hashRE.MatchString(e.Old) || e.New != "" && !hashRE.MatchString(e.New) {
		return false
	}
	switch e.Kind {
	case "baseline", "created", "modified", "restored", "recovered", "metadata_changed":
		return e.New != ""
	case "deleted", "missing_initial", "unreadable", "unstable":
		return e.New == ""
	}
	return false
}
func (s *Server) batch(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	defer func() { s.ingestNanos.Add(int64(time.Since(start))); s.ingestCount.Add(1) }()
	var b struct {
		Batch   string  `json:"batch_id"`
		Version int     `json:"schema_version"`
		Events  []Event `json:"events"`
	}
	if !decode(w, r, &b) {
		return
	}
	if b.Version != 1 || !validID(b.Batch) || len(b.Events) < 1 || len(b.Events) > 100 {
		problem(w, 422, "Lote deve usar schema_version=1 e conter 1–100 eventos")
		return
	}
	for _, ev := range b.Events {
		if !ev.valid() {
			problem(w, 422, "Evento inválido; lote não aceito")
			return
		}
	}
	tx, e := s.DB.Begin(r.Context())
	if e != nil {
		problem(w, 503, "Banco indisponível")
		return
	}
	defer tx.Rollback(r.Context())
	agent := p(r).Agent
	// Serialize each agent, including replay checks, against concurrent batches.
	if _, e = tx.Exec(r.Context(), `SELECT id FROM agents WHERE id=$1 FOR UPDATE`, agent); e != nil {
		problem(w, 503, "Agente indisponível")
		return
	}
	accepted, duplicates := []string{}, []string{}
	for _, ev := range b.Events {
		data, _ := json.Marshal(ev)
		fingerprint := digest(string(data))
		var existing string
		err := tx.QueryRow(r.Context(), `SELECT payload_hash FROM change_events WHERE agent_id=$1 AND (sequence=$2 OR event_uuid=$3) LIMIT 1`, agent, ev.Sequence, ev.UUID).Scan(&existing)
		if err == nil {
			if existing != fingerprint {
				s.ingestErrors.Add(1)
				_ = tx.Rollback(r.Context())
				_, _ = s.DB.Exec(r.Context(), `INSERT INTO audit_logs(id,organization_id,operation,target_type,target_id) SELECT $1,pr.organization_id,'ingest.sequence_conflict','agent',a.id FROM agents a JOIN servers se ON se.id=a.server_id JOIN environments en ON en.id=se.environment_id JOIN projects pr ON pr.id=en.project_id WHERE a.id=$2`, id(), agent)
				problem(w, 409, "Sequência ou UUID reutilizado com payload divergente; lote não aceito")
				return
			}
			duplicates = append(duplicates, ev.UUID)
			continue
		}
		if err != pgx.ErrNoRows {
			problem(w, 503, "Consulta indisponível")
			return
		}
		severity := "info"
		switch ev.Kind {
		case "modified", "deleted", "unreadable", "unstable", "missing_initial":
			severity = "warning"
		}
		_, e = tx.Exec(r.Context(), `INSERT INTO change_events(id,agent_id,sequence,event_uuid,file_alias,kind,old_sha256,new_sha256,file_size,mode,mtime,observed_at,payload_hash,severity) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)`, id(), agent, ev.Sequence, ev.UUID, ev.Alias, ev.Kind, ev.Old, ev.New, ev.Size, ev.Mode, ev.Mtime, ev.Observed, fingerprint, severity)
		if e != nil {
			problem(w, 503, "Gravação indisponível")
			return
		}
		_, e = tx.Exec(r.Context(), `INSERT INTO file_observations(agent_id,file_alias,sha256,state,file_size,mode,mtime,observed_at,sequence) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT(agent_id,file_alias) DO UPDATE SET sha256=EXCLUDED.sha256,state=EXCLUDED.state,file_size=EXCLUDED.file_size,mode=EXCLUDED.mode,mtime=EXCLUDED.mtime,observed_at=EXCLUDED.observed_at,sequence=EXCLUDED.sequence,received_at=now() WHERE file_observations.sequence<EXCLUDED.sequence`, agent, ev.Alias, ev.New, ev.Kind, ev.Size, ev.Mode, ev.Mtime, ev.Observed, ev.Sequence)
		if e != nil {
			problem(w, 503, "Observação indisponível")
			return
		}
		accepted = append(accepted, ev.UUID)
	}
	if tx.Commit(r.Context()) != nil {
		problem(w, 503, "Commit indisponível")
		return
	}
	s.ingested.Add(int64(len(accepted)))
	write(w, 202, map[string]any{"accepted": accepted, "duplicates": duplicates, "rejected": []string{}})
}
func (s *Server) heartbeat(w http.ResponseWriter, r *http.Request) {
	var b struct {
		Version  string    `json:"agent_version"`
		Queue    int       `json:"queue_depth"`
		Capacity *int      `json:"queue_capacity,omitempty"`
		Observed time.Time `json:"observed_at"`
	}
	if !decode(w, r, &b) {
		return
	}
	if len(b.Version) > 40 || b.Version == "" || b.Queue < 0 || b.Queue > 1000000 || b.Observed.IsZero() {
		problem(w, 422, "Heartbeat inválido")
		return
	}
	if b.Capacity != nil && (*b.Capacity < 1 || *b.Capacity > 100000) {
		problem(w, 422, "Capacidade da fila inválida")
		return
	}
	if b.Version != "0.1.0" {
		problem(w, 409, "Versão de agente incompatível")
		return
	}
	skew := time.Since(b.Observed).Abs() > 5*time.Minute
	_, e := s.DB.Exec(r.Context(), `UPDATE agents SET last_seen_at=now(),last_observed_at=$2,agent_version=$3,queue_depth=$4,clock_skew_warning=$5,queue_capacity=$6 WHERE id=$1`, p(r).Agent, b.Observed, b.Version, b.Queue, skew, b.Capacity)
	if e != nil {
		problem(w, 503, "Heartbeat indisponível")
		return
	}
	write(w, 202, map[string]any{"ok": true, "server_time": time.Now().UTC(), "clock_skew_warning": skew})
}
