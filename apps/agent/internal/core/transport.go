package core

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/google/uuid"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

type responseError struct{ status int }

func (e responseError) Error() string {
	return fmt.Sprintf("central retornou HTTP %d; lote preservado", e.status)
}

type Transport struct {
	Config Config
	Client *http.Client
}

func NewTransport(c Config) *Transport {
	return &Transport{Config: c, Client: &http.Client{Timeout: 15 * time.Second, CheckRedirect: func(r *http.Request, via []*http.Request) error { return errors.New("redirect não permitido") }}}
}
func (t *Transport) post(ctx context.Context, path string, body any, out any) error {
	fi, e := os.Stat(t.Config.Agent.TokenFile)
	if e != nil {
		return errors.New("token indisponível")
	}
	if fi.Mode().Perm()&0077 != 0 {
		return errors.New("token deve ser legível somente pelo proprietário")
	}
	b, e := os.ReadFile(t.Config.Agent.TokenFile)
	if e != nil {
		return errors.New("token indisponível")
	}
	token := strings.TrimSpace(string(b))
	if !strings.HasPrefix(token, "cs_") || len(token) != 46 {
		return errors.New("formato de token inválido")
	}
	data, e := json.Marshal(body)
	if e != nil {
		return e
	}
	req, e := http.NewRequestWithContext(ctx, "POST", strings.TrimRight(t.Config.Agent.URL, "/")+path, bytes.NewReader(data))
	if e != nil {
		return e
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	res, e := t.Client.Do(req)
	if e != nil {
		return errors.New("falha de transporte; lote preservado")
	}
	defer res.Body.Close()
	if res.StatusCode != 202 {
		return responseError{status: res.StatusCode}
	}
	d := json.NewDecoder(io.LimitReader(res.Body, 65536))
	d.DisallowUnknownFields()
	if e = d.Decode(out); e != nil {
		return errors.New("resposta incompatível; comandos e campos desconhecidos não são aceitos")
	}
	if d.Decode(&struct{}{}) != io.EOF {
		return errors.New("resposta contém dados adicionais não permitidos")
	}
	return nil
}
func (t *Transport) Flush(ctx context.Context, q *Queue) error {
	events, e := q.Pending(t.Config.Agent.Batch)
	if e != nil || len(events) == 0 {
		return e
	}
	q.Attempt()
	var reply struct {
		Accepted   []string `json:"accepted"`
		Duplicates []string `json:"duplicates"`
		Rejected   []string `json:"rejected"`
	}
	if e = t.post(ctx, "/agent/events:batch", map[string]any{"batch_id": uuid.NewString(), "schema_version": 1, "events": events}, &reply); e != nil {
		return e
	}
	allowed := map[string]bool{}
	for _, ev := range events {
		allowed[ev.UUID] = true
	}
	ids := append(reply.Accepted, reply.Duplicates...)
	seen := map[string]bool{}
	for _, v := range ids {
		if !allowed[v] || seen[v] {
			return errors.New("ACK inválido")
		}
		seen[v] = true
	}
	if len(reply.Rejected) > 0 || len(seen) != len(events) {
		return errors.New("ACK incompleto; lote preservado")
	}
	return q.Ack(ids)
}
func (t *Transport) Heartbeat(ctx context.Context, q *Queue, observed time.Time) error {
	depth, e := q.Depth()
	if e != nil {
		return e
	}
	var out struct {
		OK   bool      `json:"ok"`
		Time time.Time `json:"server_time"`
		Skew bool      `json:"clock_skew_warning"`
	}
	body := map[string]any{"agent_version": "0.1.0", "queue_depth": depth, "queue_capacity": q.Max, "observed_at": observed}
	err := t.post(ctx, "/agent/heartbeat", body, &out)
	var rejected responseError
	if errors.As(err, &rejected) && rejected.status == http.StatusUnprocessableEntity {
		// A pre-capacity server rejects unknown fields. Preserve compatibility
		// during a server rollback without dropping or modifying the local queue.
		delete(body, "queue_capacity")
		return t.post(ctx, "/agent/heartbeat", body, &out)
	}
	return err
}
