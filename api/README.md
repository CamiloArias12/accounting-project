# accounting-api

Backend de **Accounting Project**: FastAPI + SQLAlchemy async + Alembic,
sobre Postgres y Redis.

## Stack

| Paquete           | Versión |
| ----------------- | ------- |
| Python            | 3.12    |
| FastAPI           | 0.140.0 |
| Pydantic          | 2.13.4  |
| SQLAlchemy        | 2.0.51 (async, `asyncpg`) |
| Alembic           | 1.18.5  |
| redis-py          | 8.0.1   |
| Postgres / Redis  | 17 / 7 (docker-compose) |

## Requisitos

Docker. No hace falta Python en la máquina.

## Puesta en marcha

Se levanta desde el compose de la raíz del monorepo, no desde aquí:

```bash
cd ..                 # raíz del repo
cp .env.example .env
docker compose up -d
docker compose exec api alembic upgrade head
```

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

El código va montado en el contenedor, así que uvicorn recarga al editar.

## Comandos

Todos se ejecutan desde la raíz del repo, dentro del contenedor:

| Comando                                                            | Descripción            |
| ------------------------------------------------------------------ | ---------------------- |
| `docker compose exec api pytest`                                   | Tests                  |
| `docker compose exec api ruff check .`                             | Lint                   |
| `docker compose exec api ruff format .`                            | Formato                |
| `docker compose exec api mypy .`                                   | Tipos (modo strict)    |
| `docker compose exec api alembic revision --autogenerate -m "msg"` | Nueva migración        |
| `docker compose exec api alembic upgrade head`                     | Aplicar migraciones    |
| `docker compose exec api alembic downgrade -1`                     | Revertir la última     |
| `docker compose logs -f api`                                       | Logs                   |

Los tests corren sobre SQLite en memoria: no tocan el Postgres del stack.

## Imagen

`Dockerfile` multi-stage con dos targets:

- **`dev`** — incluye `requirements-dev.txt` (pytest, ruff, mypy) y arranca
  uvicorn con `--reload`.
- **`prod`** — solo `requirements.txt`, sin herramientas de desarrollo, corriendo
  como usuario `app` sin privilegios.

El target lo elige el compose: `dev` vía `docker-compose.override.yml`, `prod` en
el fichero base.

## Endpoints

| Método   | Ruta                        | Descripción                     |
| -------- | --------------------------- | ------------------------------- |
| `GET`    | `/api/v1/health`            | Liveness                        |
| `GET`    | `/api/v1/health/ready`      | Readiness (Postgres + Redis)    |
| `GET`    | `/api/v1/accounts`          | Listar cuentas (paginado)       |
| `POST`   | `/api/v1/accounts`          | Crear cuenta (409 si el código existe) |
| `GET`    | `/api/v1/accounts/{id}`     | Detalle                         |
| `PATCH`  | `/api/v1/accounts/{id}`     | Actualización parcial           |
| `DELETE` | `/api/v1/accounts/{id}`     | Eliminar                        |

## Estructura

```
api/
├── app/
│   ├── main.py           # App, CORS, lifespan
│   ├── core/config.py    # Settings vía pydantic-settings
│   ├── db/               # Base declarativa + sesión async
│   ├── cache/redis.py    # Pool de Redis
│   ├── models/           # Modelos ORM (importados en __init__ para Alembic)
│   ├── schemas/          # Schemas Pydantic
│   └── api/
│       ├── deps.py       # SessionDep, RedisDep
│       └── v1/           # Router y endpoints
├── alembic/              # Migraciones (env.py async)
├── tests/                # pytest sobre SQLite en memoria
├── Dockerfile            # Targets dev y prod
└── pyproject.toml        # ruff, mypy, pytest
```

`Account` es el catálogo de cuentas y sirve de plantilla: modelo → schema →
endpoint → test. El resto del dominio contable se construye sobre ese patrón.

## Notas

- El hook `post_write_hooks` de Alembic usa `type = exec`, así que `ruff` debe
  estar en el `PATH`. Dentro del contenedor `dev` lo está; por eso las
  migraciones se generan con `docker compose exec api`.
- `AccountType` es `enum.StrEnum` con `native_enum=False`: se persiste como
  `VARCHAR`, lo que evita tipos ENUM nativos en Postgres y permite que los tests
  corran sobre SQLite.
