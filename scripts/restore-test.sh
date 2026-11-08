#!/usr/bin/env bash
set -euo pipefail
: "${BACKUP_FILE:?Set encrypted backup path}"
: "${BACKUP_PASSPHRASE_FILE:?Set passphrase file}"
umask 077
restore_name="configsentinel-restore-$(date -u +%s)"
restore_password=$(openssl rand -hex 24)
cleanup(){ docker rm -f "$restore_name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run -d --name "$restore_name" --network none --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD="$restore_password" -e POSTGRES_USER=configsentinel -e POSTGRES_DB=configsentinel postgres:17-alpine >/dev/null
for restore_try in $(seq 1 30); do
 if docker exec "$restore_name" pg_isready -U configsentinel >/dev/null 2>&1; then break;fi
 sleep 1
done
docker exec "$restore_name" psql -U configsentinel -d configsentinel -c "
CREATE ROLE configsentinel_owner NOLOGIN;
CREATE ROLE configsentinel_migrator LOGIN;
CREATE ROLE configsentinel_runtime LOGIN;
" >/dev/null 2>&1 || true
gpg --batch --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" --decrypt "$BACKUP_FILE" 2>/dev/null | docker exec -i "$restore_name" pg_restore --exit-on-error --no-owner -U configsentinel -d configsentinel
docker exec "$restore_name" psql -U configsentinel -d configsentinel -Atc 'SELECT version FROM schema_migrations; SELECT count(*) FROM organizations; SELECT count(*) FROM change_events;'
