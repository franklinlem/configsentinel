//go:build linux

package core

import (
	"errors"
	"os"
	"path/filepath"

	"golang.org/x/sys/unix"
)

// OpenStateFile requires a pre-provisioned directory owned by the agent and
// closed to writes by other users. SQLite reopens the path for its WAL files.
func OpenStateFile(path string) (*os.File, error) {
	parent, err := unix.Openat2(unix.AT_FDCWD, filepath.Dir(path), &unix.OpenHow{
		Flags:   unix.O_RDONLY | unix.O_DIRECTORY | unix.O_CLOEXEC,
		Resolve: unix.RESOLVE_NO_SYMLINKS | unix.RESOLVE_NO_MAGICLINKS,
	})
	if err != nil {
		return nil, errors.New("diretório da fila indisponível ou inseguro")
	}
	defer unix.Close(parent)
	var dir unix.Stat_t
	if err = unix.Fstat(parent, &dir); err != nil || dir.Uid != uint32(os.Geteuid()) || dir.Mode&0022 != 0 {
		return nil, errors.New("diretório da fila deve pertencer ao agente e não ser gravável por outros usuários")
	}
	fd, err := unix.Openat(parent, filepath.Base(path), unix.O_CREAT|unix.O_RDWR|unix.O_CLOEXEC|unix.O_NOFOLLOW|unix.O_NONBLOCK, 0600)
	if err != nil {
		return nil, errors.New("arquivo da fila indisponível ou inseguro")
	}
	var info unix.Stat_t
	if err = unix.Fstat(fd, &info); err != nil || info.Mode&unix.S_IFMT != unix.S_IFREG || info.Uid != uint32(os.Geteuid()) || info.Nlink != 1 {
		unix.Close(fd)
		return nil, errors.New("arquivo da fila deve ser regular, exclusivo e pertencer ao agente")
	}
	if err = unix.Fchmod(fd, 0600); err != nil {
		unix.Close(fd)
		return nil, errors.New("permissões da fila não puderam ser protegidas")
	}
	return os.NewFile(uintptr(fd), "agent-state"), nil
}
