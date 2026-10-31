package core

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/google/uuid"
	_ "modernc.org/sqlite"
	"os"
	"path/filepath"
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
type Queue struct {
	DB  *sql.DB
	Max int
}

var ErrFull = errors.New("fila cheia: snapshot não avançou")

func OpenQueue(path, agentID string, max int) (*Queue, error) {
	if e := os.MkdirAll(filepath.Dir(path), 0700); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	f.Close()
	if e = os.Chmod(path, 0600); e != nil {
		return nil, e
	}
	db, e := sql.Open("sqlite", path)
	if e != nil {
		return nil, e
	}
	db.SetMaxOpenConns(1)
	for _, q := range []string{`PRAGMA journal_mode=WAL`, `PRAGMA synchronous=FULL`, `PRAGMA busy_timeout=5000`, `PRAGMA journal_size_limit=4194304`, `PRAGMA max_page_count=32768`, `CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)`, `CREATE TABLE IF NOT EXISTS snapshots(alias TEXT PRIMARY KEY,data TEXT NOT NULL)`, `CREATE TABLE IF NOT EXISTS events(uuid TEXT PRIMARY KEY,seq INTEGER NOT NULL UNIQUE,payload TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0)`} {
		if _, e = db.Exec(q); e != nil {
			db.Close()
			return nil, e
		}
	}
	var stored string
	e = db.QueryRow(`SELECT value FROM meta WHERE key='agent_id'`).Scan(&stored)
	if e == sql.ErrNoRows {
		_, e = db.Exec(`INSERT INTO meta VALUES('agent_id',?),('sequence','0')`, agentID)
	} else if e == nil && stored != agentID {
		e = errors.New("agent_id divergente da fila; rotação requer procedimento manual")
	}
	if e != nil {
		db.Close()
		return nil, e
	}
	return &Queue{DB: db, Max: max}, nil
}
func (q *Queue) Depth() (int, error) {
	var n int
	e := q.DB.QueryRow(`SELECT count(*) FROM events`).Scan(&n)
	return n, e
}
func (q *Queue) Observe(alias string, now Snapshot, at time.Time) error {
	tx, e := q.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	var raw string
	old := Snapshot{}
	e = tx.QueryRow(`SELECT data FROM snapshots WHERE alias=?`, alias).Scan(&raw)
	if e != nil && e != sql.ErrNoRows {
		return e
	}
	if e == nil {
		if e = json.Unmarshal([]byte(raw), &old); e != nil {
			return e
		}
	}
	kind, next := Transition(old, now)
	if kind != "" {
		var n int
		if e = tx.QueryRow(`SELECT count(*) FROM events`).Scan(&n); e != nil {
			return e
		}
		if n >= q.Max {
			return ErrFull
		}
		var seq int64
		if e = tx.QueryRow(`SELECT CAST(value AS INTEGER) FROM meta WHERE key='sequence'`).Scan(&seq); e != nil {
			return e
		}
		seq++
		ev := Event{UUID: uuid.NewString(), Sequence: seq, Alias: alias, Kind: kind, Old: old.Hash, Size: now.Size, Mode: now.Mode, Mtime: now.Mtime, Observed: at}
		if now.State == "present" {
			ev.New = now.Hash
		}
		payload, e := json.Marshal(ev)
		if e != nil {
			return e
		}
		if _, e = tx.Exec(`INSERT INTO events(uuid,seq,payload) VALUES(?,?,?)`, ev.UUID, seq, string(payload)); e != nil {
			return e
		}
		if _, e = tx.Exec(`UPDATE meta SET value=? WHERE key='sequence'`, fmt.Sprint(seq)); e != nil {
			return e
		}
	}
	data, _ := json.Marshal(next)
	if _, e = tx.Exec(`INSERT INTO snapshots VALUES(?,?) ON CONFLICT(alias) DO UPDATE SET data=excluded.data`, alias, string(data)); e != nil {
		return e
	}
	return tx.Commit()
}
func (q *Queue) Pending(n int) ([]Event, error) {
	rows, e := q.DB.Query(`SELECT payload FROM events ORDER BY seq LIMIT ?`, n)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	out := []Event{}
	for rows.Next() {
		var raw string
		if e = rows.Scan(&raw); e != nil {
			return nil, e
		}
		var ev Event
		if e = json.Unmarshal([]byte(raw), &ev); e != nil {
			return nil, e
		}
		out = append(out, ev)
	}
	return out, rows.Err()
}
func (q *Queue) Ack(ids []string) error {
	tx, e := q.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	for _, id := range ids {
		if _, e = tx.Exec(`DELETE FROM events WHERE uuid=?`, id); e != nil {
			return e
		}
	}
	return tx.Commit()
}
func (q *Queue) Attempt() {
	_, _ = q.DB.Exec(`UPDATE events SET attempts=attempts+1 WHERE uuid IN(SELECT uuid FROM events ORDER BY seq LIMIT 100)`)
}
