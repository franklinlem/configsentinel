#!/usr/bin/env bash
set -euo pipefail
# Target must be a reviewed dedicated container; output contains only this project's DB.
: "${DB_CONTAINER:?Set dedicated ConfigSentinel database container}"
: "${BACKUP_DIR:?Set encrypted backup destination}"
: "${BACKUP_PASSPHRASE_FILE:?Set 0600 passphrase file outside repo}"
case "$DB_CONTAINER" in *configsentinel*|*csentinel*) ;; *) echo 'Use the dedicated ConfigSentinel DB container name' >&2;exit 1;; esac
umask 077
mkdir -p "$BACKUP_DIR"
backup_stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_path="$BACKUP_DIR/configsentinel-$backup_stamp.dump.gpg"
docker exec "$DB_CONTAINER" pg_dump -U configsentinel -d configsentinel -Fc | gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --symmetric --cipher-algo AES256 --output "$backup_path"
sha256sum "$backup_path" > "$backup_path.sha256"
printf '%s\n' "$backup_path"
