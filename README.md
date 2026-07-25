# accounting-project

Monorepo de la plataforma de contabilidad. Todo corre en Docker.

## Estructura

```
accounting-project/
├── web/                        # Frontend — Next.js 16 + React 19 + Tailwind 4
├── api/                        # Backend  — FastAPI + SQLAlchemy async
├── docker-compose.yml          # Base = producción
└── docker-compose.override.yml # Desarrollo (Compose lo aplica solo)
```

| Servicio | Stack                                | Puerto |
| -------- | ------------------------------------ | ------ |
| `web`    | Next.js 16, React 19, Tailwind 4     | 3000   |
| `api`    | FastAPI 0.140, SQLAlchemy 2, Alembic | 8000   |
| postgres | Postgres 17                          | 5432 (solo en dev) |
| redis    | Redis 7                              | 6379 (solo en dev) |

## Requisitos

Docker. Nada más — no hace falta Node ni Python en la máquina.

## Desarrollo

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api alembic upgrade head
```

- Web: <http://localhost:3000>
- API: <http://localhost:8000> · docs en <http://localhost:8000/docs>

El código está montado en los contenedores, así que **web y API recargan solas**
al editar. Postgres y Redis quedan expuestos en el host para poder conectarte
con un cliente externo.

## Producción

`docker-compose.override.yml` se aplica automáticamente, así que para producción
hay que excluirlo pasando solo el fichero base:

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml exec api alembic upgrade head
```

Diferencias frente a dev:

- Imágenes construidas con el target `prod`: sin dependencias de desarrollo, sin
  código montado y con usuario sin privilegios (`app` en la API, `nextjs` en la web).
- Next.js se sirve desde el output `standalone`, no con `next dev`.
- Postgres y Redis **no** publican puertos en el host: solo se llega a ellos
  desde la red interna de Compose.
- `DEBUG=false` y `ENVIRONMENT=production`.

Las migraciones no se ejecutan solas al arrancar — lánzalas explícitamente para
no sorprender a un despliegue con varias réplicas.

## Comandos

Todo se ejecuta dentro de los contenedores:

| Comando                                                     | Descripción           |
| ----------------------------------------------------------- | --------------------- |
| `docker compose up -d`                                      | Levantar (dev)        |
| `docker compose down`                                       | Parar                 |
| `docker compose logs -f api`                                | Ver logs              |
| `docker compose exec api pytest`                            | Tests de la API       |
| `docker compose exec api ruff check .`                      | Lint de la API        |
| `docker compose exec api mypy .`                            | Tipos de la API       |
| `docker compose exec api alembic upgrade head`              | Aplicar migraciones   |
| `docker compose exec api alembic revision --autogenerate -m "msg"` | Nueva migración |
| `docker compose exec web npm run lint`                      | Lint de la web        |

## Variables de entorno

Todas viven en el `.env` de la raíz — ver [`.env.example`](./.env.example).
`POSTGRES_USER` y `POSTGRES_PASSWORD` son obligatorias: el compose falla si
faltan, en vez de arrancar con credenciales por defecto.

`NEXT_PUBLIC_API_URL` se inyecta en el bundle del navegador **al construir la
imagen**, no en runtime. Si cambia, hay que reconstruir la web.

## Notas

`docker-compose.yml` fija `name: accounting`. Sin un nombre explícito, Compose lo
deduce del directorio y puede recrear los contenedores de cualquier otro proyecto
que viva en una carpeta homónima.

Dev y prod usan tags de imagen distintos (`accounting-api:dev` /
`accounting-api:prod`, y lo mismo para `web`). Con un tag compartido, alternar
entre modos hace que `up` sin `--build` reutilice en silencio la imagen del otro
modo: la web arrancaba con el `CMD` de producción sobre el código montado de
desarrollo y entraba en bucle de reinicio.

Detalle de cada parte en [`web/README.md`](./web/README.md) y
[`api/README.md`](./api/README.md).

## Licencia

Por definir.
