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

- Python 3.12
- Docker (para Postgres y Redis)

## Puesta en marcha

```bash
cd api

# 1. Entorno virtual
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # o requirements.txt en producción

# 2. Configuración
cp .env.example .env

# 3. Postgres + Redis
docker compose up -d

# 4. Migraciones
alembic upgrade head

# 5. Servidor
uvicorn app.main:app --reload
```

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Comandos

| Comando                                        | Descripción              |
| ---------------------------------------------- | ------------------------ |
| `uvicorn app.main:app --reload`                | Servidor de desarrollo   |
| `pytest`                                       | Tests                    |
| `ruff check . && ruff format --check .`        | Lint y formato           |
| `mypy .`                                       | Tipos (modo strict)      |
| `alembic revision --autogenerate -m "mensaje"` | Nueva migración          |
| `alembic upgrade head`                         | Aplicar migraciones      |
| `alembic downgrade -1`                         | Revertir la última       |

Los tests corren sobre SQLite en memoria, así que no necesitan Docker.

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
├── docker-compose.yml    # Postgres + Redis
└── pyproject.toml        # ruff, mypy, pytest
```

`Account` es el catálogo de cuentas y sirve de plantilla: modelo → schema →
endpoint → test. El resto del dominio contable se construye sobre ese patrón.

## Notas

- **`name: accounting` en `docker-compose.yml` es obligatorio.** Sin él, Compose
  deduce el nombre del proyecto del directorio (`api`) y puede recrear los
  contenedores de cualquier otro proyecto que viva en una carpeta homónima.
- El hook `post_write_hooks` de Alembic usa `type = exec`, así que `ruff` debe
  estar en el `PATH` (basta con el venv activo) al generar migraciones.
- `AccountType` es `enum.StrEnum` con `native_enum=False`: se persiste como
  `VARCHAR`, lo que evita tipos ENUM nativos en Postgres y permite que los tests
  corran sobre SQLite.
