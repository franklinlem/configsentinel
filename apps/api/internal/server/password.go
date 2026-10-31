package server

import (
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"golang.org/x/crypto/argon2"
	"strings"
)

func secret() string {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return base64.RawURLEncoding.EncodeToString(b)
}
func digest(s string) string { h := sha256.Sum256([]byte(s)); return hex.EncodeToString(h[:]) }
func passwordHash(p string) string {
	salt := make([]byte, 16)
	if _, e := rand.Read(salt); e != nil {
		panic(e)
	}
	h := argon2.IDKey([]byte(p), salt, 2, 64*1024, 2, 32)
	return "argon2id$" + base64.RawStdEncoding.EncodeToString(salt) + "$" + base64.RawStdEncoding.EncodeToString(h)
}
func passwordOK(p, h string) bool {
	parts := strings.Split(h, "$")
	if len(parts) != 3 || parts[0] != "argon2id" {
		return false
	}
	s, e := base64.RawStdEncoding.DecodeString(parts[1])
	if e != nil || len(s) != 16 {
		return false
	}
	want, e := base64.RawStdEncoding.DecodeString(parts[2])
	if e != nil || len(want) != 32 {
		return false
	}
	got := argon2.IDKey([]byte(p), s, 2, 64*1024, 2, 32)
	return subtle.ConstantTimeCompare(got, want) == 1
}
