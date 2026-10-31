package server

import (
	"github.com/google/uuid"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestPasswords(t *testing.T) {
	h := passwordHash("correct test password")
	if !passwordOK("correct test password", h) || passwordOK("incorrect", h) || passwordOK("x", "broken") {
		t.Fatal("password verification")
	}
	if digest(secret()) == digest(secret()) {
		t.Fatal("randomness")
	}
}
func TestStrictJSON(t *testing.T) {
	for _, body := range []string{`{"unknown":"content"}`, `{} {}`, strings.Repeat("x", 1<<20+1)} {
		w := httptest.NewRecorder()
		r := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
		var b struct{}
		if decode(w, r, &b) {
			t.Fatal("invalid body accepted")
		}
	}
}
func TestEventValidation(t *testing.T) {
	e := Event{UUID: uuid.NewString(), Sequence: 1, Alias: "demo", Kind: "baseline", New: strings.Repeat("a", 64), Observed: time.Now().UTC()}
	if !e.valid() {
		t.Fatal("valid rejected")
	}
	e.New = "payload"
	if e.valid() {
		t.Fatal("content accepted as hash")
	}
	e.New = ""
	e.Kind = "unreadable"
	if !e.valid() {
		t.Fatal("error rejected")
	}
	e.Alias = "/etc/config"
	if e.valid() {
		t.Fatal("path exposed")
	}
}
