# accounting-api

Backend of **Accounting Project**: FastAPI + async SQLAlchemy + Alembic, on top
of Postgres and Redis.

## Stack

| Package           | Version |
| ----------------- | ------- |
| Python            | 3.12    |
| FastAPI           | 0.140.0 |
| Pydantic          | 2.13.4  |
| SQLAlchemy        | 2.0.51 (async, `asyncpg`) |
| Alembic           | 1.18.5  |
| redis-py          | 8.0.1   |
| Postgres / Redis  | 17 / 7 (docker compose) |
| openpyxl          | 3.1.5   |

## Requirements

Docker. No Python needed on the machine.

## Getting started

Brought up from the monorepo root compose, not from here:

```bash
cd ..                 # repo root
cp .env.example .env
docker compose up -d
docker compose exec api alembic upgrade head
```

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

The code is mounted into the container, so uvicorn reloads on edit.

## Commands

All run from the repo root, inside the container:

| Command                                                            | Description         |
| ------------------------------------------------------------------ | ------------------- |
| `docker compose exec api pytest`                                   | Tests               |
| `docker compose exec api ruff check .`                             | Lint                |
| `docker compose exec api ruff format .`                            | Format              |
| `docker compose exec api mypy .`                                   | Types (strict)      |
| `docker compose exec api alembic revision --autogenerate -m "msg"` | New migration       |
| `docker compose exec api alembic upgrade head`                     | Apply migrations    |
| `docker compose exec api alembic downgrade -1`                     | Revert the last one |
| `docker compose logs -f api`                                       | Logs                |

Tests run on in-memory SQLite: they never touch the stack's Postgres.

## Image

Multi-stage `Dockerfile` with two targets:

- **`dev`** — includes `requirements-dev.txt` (pytest, ruff, mypy) and runs
  uvicorn with `--reload`.
- **`prod`** — only `requirements.txt`, no dev tooling, running as the
  unprivileged `app` user.

Compose picks the target: `dev` through `docker-compose.override.yml`, `prod` in
the base file.

## Endpoints

| Method   | Path                              | Description                              |
| -------- | --------------------------------- | ---------------------------------------- |
| `GET`    | `/api/v1/health`                  | Liveness                                 |
| `GET`    | `/api/v1/health/ready`            | Readiness (Postgres + Redis)             |
| `GET`    | `/api/v1/accounts`                | List, filterable by level/parent/search  |
| `GET`    | `/api/v1/accounts/tree`           | Nested chart, or one branch of it        |
| `POST`   | `/api/v1/auth/register`           | Create a user                            |
| `POST`   | `/api/v1/auth/login`              | Exchange credentials for a token         |
| `GET`    | `/api/v1/auth/me`                 | The authenticated user                   |
| `POST`   | `/api/v1/accounts`                | Create (409 if the code is already live) |
| `POST`   | `/api/v1/accounts/import`         | Import the spreadsheet                   |
| `GET`    | `/api/v1/accounts/{code}`         | Detail                                   |
| `PATCH`  | `/api/v1/accounts/{code}`         | Partial update                           |
| `DELETE` | `/api/v1/accounts/{code}`         | Soft delete (409 if it has children)     |
| `POST`   | `/api/v1/accounts/{code}/restore` | Undo a soft delete                       |

Read endpoints take `?include_deleted=true` to see soft-deleted rows.

**Every `/accounts` endpoint needs `Authorization: Bearer <token>`**, reads
included: a chart of accounts is business data, not a public resource. The
requirement is declared once on the router, so an endpoint added later is
protected by being there rather than by someone remembering to annotate it.

Only `/health` and `/health/ready` are open, since probes run before anything
can authenticate.

`/accounts/tree` takes `root_code` and `max_depth`, and both bound the **query**,
not just the response — asking for the classes reads nine rows, not the whole
chart:

| Request                         | Rows read | Payload |
| ------------------------------- | --------- | ------- |
| `/accounts/tree`                | 2446      | 603 KB  |
| `/accounts/tree?max_depth=2`    | 397       | 116 KB  |
| `/accounts/tree?max_depth=1`    | 55        | 12.7 KB |
| `/accounts/tree?max_depth=0`    | 9         | 2 KB    |
| `/accounts/tree?root_code=1105` | 3         | 920 B   |

## Architecture

Modular monolith in vertical slices: one folder per feature, and inside it the
plain FastAPI shape — **router → service → SQLAlchemy model**, with Pydantic at
the edge.

```
api/app/
├── modules/
│   ├── accounts/
│   │   ├── puc.py       # Chart-of-accounts rules. Pure functions, no I/O
│   │   ├── models.py    # The table, and the object the service works with
│   │   ├── schemas.py   # Pydantic: what comes in and goes out
│   │   ├── service.py   # Business rules and queries. Owns the transaction
│   │   ├── importer.py  # Spreadsheet import
│   │   ├── cache.py     # Redis cache for the tree
│   │   ├── errors.py    # Business errors, unaware of HTTP
│   │   └── router.py    # Endpoints and dependency wiring
│   ├── auth/            # Same shape
│   └── health/
├── shared/              # config, database, redis, logging, error handlers
└── api/v1/router.py     # Mounts each module's router
```

**Slices, not layers-by-type.** With one feature `models/ schemas/ services/`
looks tidy; the accounting domain still has movements, journal entries, thirds
and treasury to come. Grouping by type means every new feature scatters files
across five folders and every change opens all five. A slice keeps a feature in
one place and makes it deletable.

**No repository, no domain entity, no ports.** An earlier version had them:
entities separate from the ORM, `Protocol` ports, one class per use case. It was
dropped on purpose. Over a single table a repository only forwards calls, and a
mapper between two near-identical shapes is ceremony with nothing to show for
it. The SQLAlchemy model *is* the business object.

The trade-off is real and worth stating: business rules can no longer be tested
without a database. The tests use in-memory SQLite instead, which costs a few
seconds and is what most FastAPI codebases do.

**What survives from the strict version**, because it earns its keep:

- `puc.py` has no framework and no I/O, so the code/level/parent rules are
  tested as pure functions.
- Business errors are separate from HTTP; one table in `shared/http/errors.py`
  maps them to status codes.
- The service owns the session, so **it** decides what a transaction is. The
  import commits once for the whole file — a chart of accounts committed halfway
  is worse than one not imported at all.

**Cross-module import.** `accounts/router.py` imports `CurrentUser` from
`auth/dependencies.py`. Authentication is cross-cutting, and in this style a
feature depends on the auth module much as it depends on the session. Under the
stricter layering that was a violation; here it is the normal shape.

## The account model

The PUC is a five-level hierarchy, and **the level is not declared: it is
derived from the code length**. The parent is always the prefix.

| Code       | Length | Level      | Parent   |
| ---------- | ------ | ---------- | -------- |
| `1`        | 1      | Class      | —        |
| `11`       | 2      | Group      | `1`      |
| `1105`     | 4      | Account    | `11`     |
| `110505`   | 6      | Subaccount | `1105`   |
| `11050501` | > 6    | Auxiliary  | `110505` |

Hence **one self-referencing table**, not five. The reference project used a
table per level plus a shared table joined `OneToOne` to each; since the
hierarchy already lives in the accounting code, that split only duplicated
columns and relationships.

Rules the service enforces:

- Creating an account requires its parent to exist.
- Deleting an account that still has live children returns 409, and the foreign
  key blocks it anyway with `ON DELETE RESTRICT`.
- The code is immutable: changing it would move the account elsewhere in the
  tree, so `PATCH` refuses it.

### Soft delete

Rows are never removed. `DELETE` stamps `deleted_at`, and every read hides those
rows unless `include_deleted=true` is passed. Accounting records must stay
auditable, and a deleted code must not be silently reused by a different
account.

Two flags that are easy to confuse:

- `is_active` — a business flag: the account exists but may not be posted to.
- `deleted_at` — the account is gone from the chart.

Creating an account whose code is soft-deleted revives that row with the new
data: the primary key is still taken, and reviving is what "create it again"
means. Restoring is refused while the parent is still deleted.

## Importing the chart of accounts

```bash
curl -X POST http://localhost:8000/api/v1/accounts/import \
  -F "file=@plan-de-cuentas-solidario.xlsx"
```

Expected columns: `Codigo`, `Nombre`, `Tipo`, `Naturaleza`.

- `Tipo` is redundant (the level comes from the code) and is only used to flag
  inconsistencies.
- Rows are sorted by depth before inserting, so **the file order does not
  matter**: a parent always lands before its children.
- It is partial and transparent: valid rows go in, failing rows come back with
  their row number and the reason.
- `?on_existing=skip|update` decides what happens to accounts already stored.

## Authentication

JWT bearer tokens. Passwords are hashed with Argon2id via `pwdlib`.

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@acme.com","password":"sup3r-secret-1","full_name":"Admin"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=admin@acme.com&password=sup3r-secret-1'
```

Login answers the same 401 whether the email is unknown or the password is
wrong, and verifies a hash either way, so neither the message nor the response
time reveals which accounts exist.

`JWT_SECRET` has a development default that **the settings refuse outside
`ENVIRONMENT=local`**: startup fails rather than shipping a guessable signing
key. Generate one with `openssl rand -hex 32`.

## Operations

- **Connection pool.** `DB_POOL_SIZE` + `DB_MAX_OVERFLOW` per replica; multiply
  by the replica count and keep it under Postgres `max_connections`.
- **Cache.** `CACHE_TTL_SECONDS` bounds staleness if an invalidation is ever
  missed; every write drops the namespace anyway.
- **Logs** are JSON on stdout, each line carrying `request_id`. The same id is
  returned in `X-Request-ID`, and an incoming one is reused so a trace survives
  across services.
- **Import** works in batches of 500, so neither the entity list nor an
  `IN (...)` grows with the file.

## Notes

- Alembic's `post_write_hooks` uses `type = exec`, so `ruff` must be on `PATH`.
  It is inside the `dev` container, which is why migrations are generated with
  `docker compose exec api`.
- `Nature` and `AccountLevel` are `enum.StrEnum` with `native_enum=False`: they
  persist as `VARCHAR`, avoiding native Postgres ENUM types and letting the
  tests run on SQLite. Their values stay Spanish because they are the contract
  with the source spreadsheet.
- Listing methods are called `find_many`, not `list`: inside the class a method
  named `list` shadows the builtin and breaks annotations like
  `list[AccountNode]`.
