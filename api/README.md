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
| `GET`    | `/api/v1/accounts/tree`           | Nested chart of accounts                 |
| `POST`   | `/api/v1/accounts`                | Create (409 if the code is already live) |
| `POST`   | `/api/v1/accounts/import`         | Import the spreadsheet                   |
| `GET`    | `/api/v1/accounts/{code}`         | Detail                                   |
| `PATCH`  | `/api/v1/accounts/{code}`         | Partial update                           |
| `DELETE` | `/api/v1/accounts/{code}`         | Soft delete (409 if it has children)     |
| `POST`   | `/api/v1/accounts/{code}/restore` | Undo a soft delete                       |

Read endpoints take `?include_deleted=true` to see soft-deleted rows.

## Layout

Layered, innermost first. Each layer only knows the one below it:

```
api/
├── app/
│   ├── domain/puc.py     # PUC rules. No I/O: level, parent, validation
│   ├── models/           # ORM (imported in __init__ for Alembic)
│   ├── schemas/          # Pydantic request/response contracts
│   ├── repositories/     # Data access, no business rules
│   ├── services/         # Business rules + spreadsheet import
│   │   └── errors.py     # Domain errors, unaware of HTTP
│   ├── api/
│   │   ├── deps.py       # Session, repository and service injection
│   │   ├── errors.py     # Maps domain errors to HTTP status codes
│   │   └── v1/           # Router and endpoints (thin layer)
│   ├── core/config.py    # Settings via pydantic-settings
│   ├── db/               # Declarative base + async session
│   └── cache/redis.py    # Redis pool
├── alembic/              # Migrations (async env.py)
├── tests/                # pytest on in-memory SQLite
├── Dockerfile            # dev and prod targets
└── pyproject.toml        # ruff, mypy, pytest
```

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
