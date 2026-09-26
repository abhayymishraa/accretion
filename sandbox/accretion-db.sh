#!/bin/sh
# Start or stop one database server inside the sandbox, as the sandbox user (spec 8: services
# start only when the kit asks for them). Idempotent: `start` on a running server is a no-op.
# Usage: accretion-db start|stop|reset postgres|mongo
set -eu
PG_BIN=/usr/lib/postgresql/18/bin
PG_DATA=/home/user/.pg
MONGO_DATA=/home/user/.mongo

pg_ready() { pg_isready -q -h 127.0.0.1 -p 5432; }
mongo_ready() { mongosh --quiet --eval 'db.runCommand({ping: 1}).ok' 2>/dev/null | grep -q 1; }

case "$1:$2" in
  start:postgres) pg_ready || "$PG_BIN/pg_ctl" -D "$PG_DATA" -l "$PG_DATA/server.log" -w start >/dev/null ;;
  stop:postgres) "$PG_BIN/pg_ctl" -D "$PG_DATA" -w stop >/dev/null 2>&1 || true ;;
  reset:postgres)
    dropdb -h 127.0.0.1 -U user --if-exists app
    createdb -h 127.0.0.1 -U user -O app app ;;
  start:mongo)
    mongo_ready || mongod --dbpath "$MONGO_DATA" --bind_ip 127.0.0.1 --fork --logpath "$MONGO_DATA/mongod.log" >/dev/null ;;
  stop:mongo) mongod --dbpath "$MONGO_DATA" --shutdown >/dev/null 2>&1 || true ;;
  reset:mongo) mongosh --quiet app --eval 'db.dropDatabase()' >/dev/null ;;
  *) echo "usage: accretion-db start|stop|reset postgres|mongo" >&2; exit 2 ;;
esac
