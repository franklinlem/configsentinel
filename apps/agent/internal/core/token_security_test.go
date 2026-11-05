//go:build linux

package core

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestTokenReadRequiresPrivateRegularFileWithoutSymlinks(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "token")
	token := "cs_" + strings.Repeat("a", 43)
	if err := os.WriteFile(path, []byte(token+"\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if got, err := readToken(path); err != nil || got != token {
		t.Fatalf("valid private token rejected: %v", err)
	}
	link := filepath.Join(dir, "link")
	if err := os.Symlink(path, link); err != nil {
		t.Fatal(err)
	}
	if _, err := readToken(link); err == nil {
		t.Fatal("symlink accepted")
	}
	parent := filepath.Join(dir, "parent-link")
	if err := os.Symlink(dir, parent); err != nil {
		t.Fatal(err)
	}
	if _, err := readToken(filepath.Join(parent, "token")); err == nil {
		t.Fatal("symlinked parent accepted")
	}
	if err := os.Chmod(path, 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := readToken(path); err == nil {
		t.Fatal("world-readable token accepted")
	}
	if err := os.Chmod(path, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(strings.Repeat("x", 129)), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readToken(path); err == nil {
		t.Fatal("oversized token accepted")
	}
}
