//go:build linux

package core

import (
	"os"
	"path/filepath"
	"testing"
)

func TestStateFileRejectsLinksAndUnsafeParent(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, "target")
	if err := os.WriteFile(target, []byte("preserve"), 0644); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(dir, "queue")
	if err := os.Symlink(target, link); err != nil {
		t.Fatal(err)
	}
	if _, err := OpenStateFile(link); err == nil {
		t.Fatal("symlink accepted")
	}
	info, err := os.Stat(target)
	if err != nil || info.Mode().Perm() != 0644 {
		t.Fatal("symlink target was modified")
	}
	if err := os.Remove(link); err != nil {
		t.Fatal(err)
	}
	if err := os.Link(target, link); err != nil {
		t.Fatal(err)
	}
	if _, err := OpenStateFile(link); err == nil {
		t.Fatal("hard link accepted")
	}
	if err := os.Remove(link); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(dir, 0777); err != nil {
		t.Fatal(err)
	}
	if _, err := OpenStateFile(link); err == nil {
		t.Fatal("writable parent accepted")
	}
	if err := os.Chmod(dir, 0700); err != nil {
		t.Fatal(err)
	}
	f, err := OpenStateFile(link)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	info, err = f.Stat()
	if err != nil || info.Mode().Perm() != 0600 {
		t.Fatal("state file not private")
	}
}
