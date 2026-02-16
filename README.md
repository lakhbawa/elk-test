# Node.js PostgreSQL Read/Write Replica Demo

A minimal Node.js project demonstrating:

- **Write traffic** sent to a PostgreSQL **primary**.
- **Read traffic** served from a PostgreSQL **read replica**.
- **Adminer** UI for visualizing both databases.

> This is intentionally minimal. Later, this project can be extended with sharding and partitioning examples.

## Stack

- Node.js 20
- `pg` driver
- PostgreSQL 16 (Bitnami images)
- Docker Compose
- Adminer

## Project structure

- `src/demo.js`: writes a row on primary, then polls replica until row appears.
- `src/config.js`: connection config from env vars.
- `docker-compose.yml`: primary + replica + adminer + app.

## Run with Docker Compose

```bash
docker compose up --build
```

When successful, app logs should show something like:

- `WROTE_ON_PRIMARY: ...`
- `READ_ON_REPLICA: ...`
- `SUCCESS: write to primary + read from replica demonstrated.`

Stop everything:

```bash
docker compose down
```

If you want to reset data:

```bash
docker compose down -v
```

## Adminer visualization

Open: <http://localhost:8080>

Use one of these connections:

### Primary
- System: `PostgreSQL`
- Server: `postgres-primary`
- Username: `app`
- Password: `app_password`
- Database: `appdb`

### Replica
- System: `PostgreSQL`
- Server: `postgres-replica`
- Username: `app`
- Password: `app_password`
- Database: `appdb`

## Local (without Docker app service)

If you already have Node.js installed locally:

```bash
npm install
npm run demo
```

By default it expects:

- Primary: `localhost:5432`
- Replica: `localhost:5433`
- User: `app`
- Password: `app_password`
- Database: `appdb`

## Next step ideas

- Add simple read/write query router abstraction.
- Add sharding demo by user ID hash across multiple primaries.
- Add partitioning demo (range partition on `created_at`).
