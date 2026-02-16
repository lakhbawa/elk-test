#!/usr/bin/env bash
set -euo pipefail

: "${PGDATA:=/var/lib/postgresql/data}"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "[replica] Initializing replica data directory from primary..."
  rm -rf "${PGDATA:?}"/*

  until PGPASSWORD="${REPLICATION_PASSWORD}" pg_basebackup \
    -h "${PRIMARY_HOST}" \
    -p "${PRIMARY_PORT}" \
    -U "${REPLICATION_USER}" \
    -D "${PGDATA}" \
    -Fp \
    -Xs \
    -R; do
    echo "[replica] Waiting for primary to be ready..."
    sleep 2
  done

  chown -R postgres:postgres "$PGDATA"
  chmod 700 "$PGDATA"
fi

exec docker-entrypoint.sh postgres
