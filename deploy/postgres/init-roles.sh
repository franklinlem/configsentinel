#!/bin/sh
set -eu
: "${CONFIGSENTINEL_RUNTIME_PASSWORD:?runtime password required}"
: "${CONFIGSENTINEL_MIGRATOR_PASSWORD:?migrator password required}"
# Credentials stay in the environment and psql memory, not command arguments.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --file /opt/configsentinel/provision.sql
