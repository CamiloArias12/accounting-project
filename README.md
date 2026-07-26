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

## Screens

| Path             | What it does                                                              |
| ---------------- | ------------------------------------------------------------------------- |
| `/accounts`      | The chart as a tree: search, create, edit, soft-delete, restore, import    |
| `/third-parties` | Natural and legal persons, with the DANE places and the NIT check digit    |
| `/vouchers`      | List and editor; save a draft, post it, reverse a posted one              |
| `/ledger`        | Balances per account, and one account's movements with a running balance   |
| `/periods`       | The twelve months of a year, closed and reopened                          |
| `/exogena`       | Generate the XML, download an earlier one, and manage the UVT behind it    |

Everything is Spanish or English at a click, and the language is a cookie, not a
URL segment.

## Design decisions

### The code is the hierarchy

The level is the code's length and the parent is its prefix. That is not a
shortcut but what the PUC actually is: `110505` *is* inside `1105` because of
how it is written. Both are derived on the way in and never asked of the caller,
so the two cannot disagree.

`parent_code` is still a real column with a foreign key — derived, but stored,
so the database can refuse to delete a parent that still has children even if
the service check were bypassed. What it is not is the *source* of the
relationship: change a code and the parent is recomputed from it, never the
reverse.

Reading a whole branch is then one `LIKE '1105%'` rather than a recursive query.
The cost is that a code cannot be renamed without moving its children, which is
the correct trade: in the PUC the code is the identity.

### Only the leaves take entries

A voucher line may only name an account with nothing under it. Posting to
`1105` when `110505` exists would double-count it in every report that walks the
tree. The check is at the domain layer, so it holds for the API, the import and
anything added later.

### Balances are computed, never stored

There is no running-balance column and no per-account totals table. The ledger
is what the posted voucher lines add up to, and keeping a second copy means the
two drift the first time a write fails halfway — the classic accounting bug
where the balance and the movements no longer agree and nobody knows which is
right.

The report gets the opening balance and the movement in **one** query:
conditional aggregation over two slices of dates rather than two round trips.
The account detail's running balance is accumulated in order of date and
consecutive number, which is the order the books were written in and the only
order in which a running balance means anything.

If this became slow it would be a materialised view refreshed on posting, not a
column — the derivation stays in one place either way.

### Balance is a precondition of posting, not a report footer

Debits must equal credits before a voucher can enter the books, and a voucher
needs at least two lines. The reference project computes those totals only to
print them, so an unbalanced entry saves happily and the trial balance quietly
stops balancing. Here `totals.is_balanced` in the ledger is a consequence, not a
check: if every voucher balanced, the books as a whole add up to zero.

### Draft and posted

A draft is a working document — editable, deletable, outside the balances. A
posted voucher has a consecutive number and cannot be altered at all, only
reversed. That is the line between a document someone is still writing and an
accounting record.

### Reversal instead of deletion

A posted mistake is corrected by writing the entry that cancels it: same
accounts, debits and credits swapped, posted in the same operation. Leaving the
correction as a draft would be worse than either state, because the books show
only the mistake until somebody remembers to finish. The pair stays visible —
the original is marked as reversed, the reversal points back at it.

### Period closing, and reopening

Only *closed* periods have a row. A month with no row is open, so the books can
be used before anyone has created a single period, and closing 2025-06 does not
require the eleven other months to exist.

Reopening is allowed and deliberately so: a period is closed to stop accidental
entries, not to make the past unreachable, and a close that cannot be undone
turns a mistyped month into a permanent one. Every change records who made it
and when, which is the part that actually matters for an audit.

### The company is configuration

`COMPANY_NIT` and `COMPANY_LEGAL_NAME` are settings, not a table. The whole
database belongs to one company, so a `companies` table would have exactly one
row and every query would carry a foreign key that can only take one value —
multi-tenancy's costs with none of its benefits. The spec lists "empresa" as a
field of the voucher; here it is the same value for every voucher in the
database, so it is printed on the screen and stamped into the exógena file
rather than stored a thousand times.

If the product ever hosted several companies, the change is a tenant column and
a scoped session — not the removal of one that was never load-bearing.

### Concurrency

Two postings racing for the same consecutive number is the one race that
matters, and it is settled by a unique index rather than by a lock: the loser
gets an `IntegrityError`, rolls back, and retries with the next number. A
`SELECT max(number)` under a lock would serialise every posting in the system to
protect against something that happens rarely.

Everything else relies on the database's own guarantees. A voucher and its lines
are written in one transaction; the ledger reads a single snapshot; the UVT
refresh is idempotent because the year is unique, so running it every night
updates one row rather than accumulating them.

### Money

`Numeric(18,2)` in Postgres, `Decimal` in Python, decimal strings over HTTP, and
integer cents in the browser. A float never touches an amount at any point: the
server refuses an entry that is off by a hundredth, so the total the user is
watching has to be the same figure the server will check.

### Exógena and the UVT

The report is built from posted vouchers, grouped by third party and DIAN
concept, and rounded to whole pesos per row before totalling — the file the DIAN
takes has no cents. Every generation is stored with the bytes it produced, so
re-downloading gives what was filed rather than what the books would say today;
a reversal landing afterwards must not change a document already sent.

The UVT is fetched from a published table over the network, kept per year, and
recorded with every attempt — including the failures, because a threshold that
quietly used a stale UVT is exactly what the run log exists to make visible. A
value typed in by hand outranks the source and is never overwritten by a fetch.
A threshold of zero needs no UVT at all, which is what keeps the report usable
for a year nobody has published one for yet.

## Limitations

Known, and deliberate for a five-day exercise:

- **One company, one currency, no multi-tenancy.** See above.
- **No user administration.** Users exist and authenticate; there is no screen
  to create them and no roles — every signed-in user can do everything.
- **The exógena format is the simplified one from the spec**, not the DIAN's
  real 1001 specification, which is dozens of formats with their own layouts.
- **No closing entry.** Closing a period stops entries in it; it does not cancel
  income and expense accounts into equity for the year.
- **No attachments on vouchers**, no PDF output, no printed reports.
- **The UVT source is a third-party page.** It is parsed defensively and every
  attempt is logged, but a layout change there breaks the fetch — hence the
  manual override.
- **Pagination is offset-based.** Fine for these volumes; a table of millions of
  vouchers would want keyset pagination, since `OFFSET 900000` still walks
  900,000 rows.

## What would change for production

- **The consecutive becomes per-book.** Real bookkeeping numbers vouchers by
  type (CE, CI, CC…), not one series for everything. The retry-on-conflict
  mechanism is unchanged; only the scope of the uniqueness moves.
- **Audit trail on every write.** Vouchers record who created and posted them
  and periods who closed them, but master data does not — a `who/when/what`
  table would cover the rest.
- **Background jobs move out of the request.** The UVT refresh runs in a
  FastAPI background task, which dies with the process. Redis is already in the
  stack; this belongs in a worker with retries that survive a restart.
- **Rate limiting and lockout on the login endpoint**, which today will accept
  attempts as fast as they arrive.
- **Observability beyond the logs.** Every line is JSON and carries a request id
  echoed back in `X-Request-ID`, which makes one call traceable across replicas.
  There are still no metrics and no tracing, and "the ledger got slow" is not
  answerable without them.
- **Backups, and a restore that has actually been run.** An untested backup is a
  belief, not a backup.

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

## Live instance

<http://46.224.38.172:3001> — sign in with `demo@accounting-project.dev` /
`demo-accounting-2026`. The Colombian PUC is already loaded: 2.446 accounts
across the five levels, so the tree, the search and the account picker have
something real in them.

It is a demonstration box, not a service with an uptime guarantee, and it shares
the host with an unrelated production application. That is why the app sits on
port 3001 and the API listens on loopback only: the web reaches it over the
Compose network, and nothing else needs to.

## Continuous integration and deployment

`.github/workflows/ci.yml` runs on every push and pull request: ruff, mypy and
pytest for the API, ESLint, `tsc` and a production build for the web. Every
check runs inside this repository's own images, so the Dockerfiles are exercised
by the same job that lints the code.

On `main`, once the checks pass, the images are published to GHCR and the server
is updated:

```
push a main → checks → imágenes a ghcr.io → aprovisionar → desplegar → verificar
```

Two scripts carry the deployment, both idempotent:

- [`scripts/provision.sh`](./scripts/provision.sh) — installs Docker if it is
  missing and generates the server's `.env` with random credentials, once. It is
  never regenerated: the Postgres password is baked into the volume the first
  time it initialises, and rotating `JWT_SECRET` would sign everyone out on
  every push.
- [`scripts/deploy.sh`](./scripts/deploy.sh) — fetches the exact commit,
  migrates with the new image *before* swapping the containers, brings the stack
  up and waits for the health endpoint. It refuses to run if a container of ours
  belongs to another Compose project, if a port is taken by a foreign process,
  or if there is under 2 GB of free disk.

Nothing is built on the server. It has 3.7 GB of RAM shared with somebody else's
production database, and a `next build` there could invoke the OOM killer or
fill the disk. The images arrive from the registry, already built.

One step cannot be automated, because until it exists GitHub has no way in:
installing the deploy key. [`scripts/setup-github-deploy.sh`](./scripts/setup-github-deploy.sh)
does it in one command — generates the key, installs it, and uploads
`SSH_PRIVATE_KEY`, `DEPLOY_HOST` and `SSH_KNOWN_HOSTS` to the repository:

```bash
./scripts/setup-github-deploy.sh <ip-del-servidor>
```

Without those secrets the deploy job exits green and says so: the pipeline is
not broken, it is unconfigured.

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
