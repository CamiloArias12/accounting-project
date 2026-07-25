# accounting-project

Monorepo for the accounting platform. Everything runs in Docker.

## Layout

```
accounting-project/
├── web/                        # Frontend — Next.js 16 + React 19 + Tailwind 4
├── api/                        # Backend  — FastAPI + async SQLAlchemy
├── docker-compose.yml          # Base = production
└── docker-compose.override.yml # Development (Compose applies it automatically)
```

| Service  | Stack                                | Port               |
| -------- | ------------------------------------ | ------------------ |
| `web`    | Next.js 16, React 19, Tailwind 4     | 3000               |
| `api`    | FastAPI 0.140, SQLAlchemy 2, Alembic | 8000               |
| postgres | Postgres 17                          | 5432 (dev only)    |
| redis    | Redis 7                              | 6379 (dev only)    |

## Chart of accounts

The implemented domain is the Colombian PUC: a five-level hierarchy where **the
level is derived from the code length** and the parent is its prefix.

```
1        Class       ACTIVOS
11       Group         DISPONIBLE
1105     Account         CAJA
110505   Subaccount        CAJA GENERAL
11050501 Auxiliary           (any longer code)
```

At <http://localhost:3000/accounts> you can browse the tree, search, create and
edit accounts, soft-delete and restore them, and import the spreadsheet. The
model and the import are documented in [`api/README.md`](./api/README.md).

## Requirements

Docker. Nothing else — no Node, no Python on the machine.

## Development

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
```

- Web: <http://localhost:3000>
- API: <http://localhost:8000> · docs at <http://localhost:8000/docs>

The code is mounted into the containers, so **web and API both reload on edit**.
Postgres and Redis are published on the host so you can attach an external
client.

## Production

`docker-compose.override.yml` is applied automatically, so production means
passing only the base file:

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml exec api alembic upgrade head
```

Differences from development:

- Images built from the `prod` target: no dev dependencies, no mounted code, and
  an unprivileged user (`app` in the API, `nextjs` in the web).
- Next is served from its `standalone` output, not `next dev`.
- Postgres and Redis publish **no** host ports: they are reachable only from the
  Compose network.
- `DEBUG=false` and `ENVIRONMENT=production`.

Migrations do not run on startup — trigger them explicitly, so a multi-replica
deploy never races itself.

## Commands

Everything runs inside the containers:

| Command                                                            | Description        |
| ------------------------------------------------------------------ | ------------------ |
| `docker compose up -d`                                             | Start (dev)        |
| `docker compose down`                                              | Stop               |
| `docker compose logs -f api`                                       | Logs               |
| `docker compose exec api pytest`                                   | API tests          |
| `docker compose exec api ruff check .`                             | API lint           |
| `docker compose exec api mypy .`                                   | API types          |
| `docker compose exec api alembic upgrade head`                     | Apply migrations   |
| `docker compose exec api alembic revision --autogenerate -m "msg"` | New migration      |
| `docker compose exec web npm run lint`                             | Web lint           |
| `docker compose exec web npm run typecheck`                        | Web types          |

## Environment

Everything lives in the root `.env` — see [`.env.example`](./.env.example).
`POSTGRES_USER` and `POSTGRES_PASSWORD` are mandatory: Compose fails rather than
starting with default credentials.

The web talks to the API **from the server only** (Server Components and Server
Actions), through the Compose service name. That is why `API_URL` is not
`NEXT_PUBLIC_*`: it never reaches the browser, is not baked into the bundle, and
changing it does not require rebuilding the image.

## Notes

`docker-compose.yml` pins `name: accounting`. Without an explicit name, Compose
derives one from the directory and can recreate the containers of any other
project living in a directory with the same name.

Dev and prod use different image tags (`accounting-api:dev` /
`accounting-api:prod`, likewise for `web`). With a shared tag, switching modes
makes `up` without `--build` silently reuse the other mode's image: the web
would boot with the production `CMD` on top of the development bind mount and
restart-loop.

## License

To be defined.
