# PostgreSQL 17.11 unchanged; remove the obsolete Go-based privilege helper.
FROM postgres:17-alpine@sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b
# These upstream scripts only need `exec gosu postgres command...`.
RUN apk add --no-cache su-exec=0.3-r0 \
 && sed -i 's/exec gosu /exec su-exec /g' /usr/local/bin/docker-entrypoint.sh /usr/local/bin/docker-ensure-initdb.sh \
 && rm /usr/local/bin/gosu \
 && su-exec postgres sh -c 'test "$(id -u)" = 70'
COPY db/roles/provision.sql /opt/configsentinel/provision.sql
COPY deploy/postgres/init-roles.sh /docker-entrypoint-initdb.d/10-configsentinel-roles.sh
