# accounting-project

Monorepo de la plataforma de contabilidad.

## Estructura

```
accounting-project/
├── web/    # Frontend — Next.js 16 + React 19 + Tailwind 4
└── api/    # Backend  — FastAPI + SQLAlchemy async + Postgres + Redis
```

| Paquete         | Stack                                   | Puerto |
| --------------- | --------------------------------------- | ------ |
| [`web/`](./web) | Next.js 16, React 19, Tailwind 4        | 3000   |
| [`api/`](./api) | FastAPI 0.140, SQLAlchemy 2, Alembic    | 8000   |

## Requisitos

- Node.js 20.9+
- Python 3.12
- Docker (Postgres y Redis para la API)

## Empezar

**API**

```bash
cd api
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d      # Postgres + Redis
alembic upgrade head
uvicorn app.main:app --reload
```

**Web**

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

- Web: <http://localhost:3000>
- API: <http://localhost:8000> · docs en <http://localhost:8000/docs>

Detalle en [`web/README.md`](./web/README.md) y [`api/README.md`](./api/README.md).

## Licencia

Por definir.
