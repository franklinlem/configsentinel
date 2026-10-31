//go:build linux

package core

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"golang.org/x/sys/unix"
	"io"
	"os"
	"time"
)

type Snapshot struct {
	State string     `json:"state"`
	Hash  string     `json:"hash"`
	Size  int64      `json:"size"`
	Mode  int64      `json:"mode"`
	Mtime *time.Time `json:"mtime"`
	Ever  bool       `json:"ever"`
}

func safeOpen(path string) (*os.File, error) {
	fd, e := unix.Openat2(unix.AT_FDCWD, path, &unix.OpenHow{Flags: unix.O_RDONLY | unix.O_CLOEXEC | unix.O_NONBLOCK | unix.O_NOFOLLOW, Resolve: unix.RESOLVE_NO_SYMLINKS | unix.RESOLVE_NO_MAGICLINKS})
	if e != nil {
		return nil, e
	}
	return os.NewFile(uintptr(fd), "authorized-file"), nil
}
func Scan(path string, limit int64) Snapshot {
	f, e := safeOpen(path)
	if e != nil {
		if errors.Is(e, unix.ENOENT) {
			return Snapshot{State: "missing"}
		}
		return Snapshot{State: "unreadable"}
	}
	defer f.Close()
	var before, after unix.Stat_t
	if unix.Fstat(int(f.Fd()), &before) != nil {
		return Snapshot{State: "unreadable"}
	}
	if before.Mode&unix.S_IFMT != unix.S_IFREG || before.Nlink != 1 || before.Size > limit || before.Size < 0 {
		return Snapshot{State: "unreadable"}
	}
	h := sha256.New()
	n, e := io.Copy(h, io.LimitReader(f, limit+1))
	if e != nil || n > limit {
		return Snapshot{State: "unreadable"}
	}
	if unix.Fstat(int(f.Fd()), &after) != nil {
		return Snapshot{State: "unstable"}
	}
	g, e := safeOpen(path)
	if e != nil {
		return Snapshot{State: "unstable"}
	}
	defer g.Close()
	var current unix.Stat_t
	if unix.Fstat(int(g.Fd()), &current) != nil || before.Ino != after.Ino || before.Dev != after.Dev || before.Size != after.Size || before.Mtim != after.Mtim || before.Ctim != after.Ctim || before.Mode != after.Mode || after.Nlink != 1 || n != after.Size || after.Ino != current.Ino || after.Dev != current.Dev || after.Ctim != current.Ctim {
		return Snapshot{State: "unstable"}
	}
	mtime := time.Unix(after.Mtim.Sec, after.Mtim.Nsec).UTC()
	return Snapshot{State: "present", Hash: hex.EncodeToString(h.Sum(nil)), Size: n, Mode: int64(after.Mode & 07777), Mtime: &mtime, Ever: true}
}
func Transition(old Snapshot, now Snapshot) (string, Snapshot) {
	kind := ""
	switch now.State {
	case "present":
		switch {
		case old.State == "":
			kind = "baseline"
		case old.State == "missing" && !old.Ever:
			kind = "created"
		case old.State == "missing":
			kind = "restored"
		case old.Hash != "" && old.Hash != now.Hash:
			kind = "modified"
		case old.State == "unreadable" || old.State == "unstable":
			kind = "recovered"
		case old.Mode != now.Mode || old.Size != now.Size || !sameTime(old.Mtime, now.Mtime):
			kind = "metadata_changed"
		}
	case "missing":
		if old.State == "" {
			kind = "missing_initial"
		} else if old.State != "missing" {
			kind = "deleted"
		}
		now.Hash = old.Hash
		now.Ever = old.Ever
	case "unreadable", "unstable":
		if old.State != now.State {
			kind = now.State
		}
		now.Hash = old.Hash
		now.Ever = old.Ever
	}
	return kind, now
}
func sameTime(a, b *time.Time) bool {
	if a == nil || b == nil {
		return a == b
	}
	return a.Equal(*b)
}
