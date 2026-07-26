#!/usr/bin/env bash
#
# Despliegue en el servidor de producción. Lo ejecuta el workflow de CI por
# stdin (`ssh host bash -s < scripts/deploy.sh`), así que aquí dentro no hay
# nada del repo todavía: lo primero que hace es traerlo.
#
# Variable de entrada: DEPLOY_SHA — el commit exacto a desplegar. Desplegar por
# SHA y no por `origin/main` evita que un push que llegue entre el checkout de
# CI y este momento se cuele sin haber pasado los checks.

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/accounting-project}"
REPO_URL="${REPO_URL:-https://github.com/CamiloArias12/accounting-project.git}"
COMPOSE=(docker compose -f docker-compose.yml)

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }

if [ -z "${DEPLOY_SHA:-}" ]; then
  echo "Falta DEPLOY_SHA: no sé qué commit desplegar." >&2
  exit 1
fi

log "Sincronizando el código en $APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
git fetch --prune origin
# reset --hard, no merge: el servidor es un reflejo del repo, nunca origen de
# cambios. Si alguien editó a mano, se pierde, y eso es lo correcto.
git reset --hard "$DEPLOY_SHA"
git clean -fd

# Red de seguridad: provision.sh ya lo generó. Si falta, algo salió mal antes
# y es mejor parar que arrancar Postgres con credenciales a medias.
if [ ! -f .env ]; then
  echo "Falta $APP_DIR/.env — provision.sh debería haberlo creado." >&2
  exit 1
fi

log "Construyendo las imágenes de producción"
"${COMPOSE[@]}" build

log "Aplicando migraciones"
# Antes de levantar el código nuevo, y con la imagen nueva: si la migración
# falla, los contenedores viejos siguen sirviendo con el esquema viejo.
# `run` respeta depends_on, así que espera a que Postgres esté healthy.
"${COMPOSE[@]}" up -d postgres redis
"${COMPOSE[@]}" run --rm api alembic upgrade head

log "Levantando los servicios"
"${COMPOSE[@]}" up -d --remove-orphans

log "Verificando que la API responda"
# El healthcheck de compose ya lo comprueba, pero desde fuera confirma también
# que el puerto está publicado.
api_port="$(grep -E '^API_PORT=' .env | cut -d= -f2)"
for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:${api_port:-8000}/api/v1/health" >/dev/null; then
    log "Despliegue correcto: $(git rev-parse --short HEAD)"
    "${COMPOSE[@]}" ps
    # Las imágenes viejas se acumulan y llenan el disco del VPS.
    docker image prune -f >/dev/null
    exit 0
  fi
  sleep 2
done

echo "La API no respondió tras 60s. Últimos logs:" >&2
"${COMPOSE[@]}" logs --tail 50 api >&2
exit 1
