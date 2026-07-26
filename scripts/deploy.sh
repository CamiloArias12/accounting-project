#!/usr/bin/env bash
#
# Despliegue en el servidor. Lo ejecuta el workflow por stdin
# (`ssh host bash -s < scripts/deploy.sh`), así que aquí no hay nada del repo
# todavía: lo primero es traerlo.
#
# Entradas:
#   DEPLOY_SHA  commit exacto a desplegar (obligatorio)
#   IMAGE_TAG   etiqueta de las imágenes en ghcr.io (por defecto, el SHA)
#
# El servidor es COMPARTIDO: jorgedarek-app corre en producción en la misma
# máquina. De ahí las comprobaciones previas y que no se construya nada aquí.

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/accounting-project}"
REPO_URL="${REPO_URL:-https://github.com/CamiloArias12/accounting-project.git}"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.server.yml)
PROJECT=accounting

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }
fail() { printf '\n\033[1;31mABORTADO:\033[0m %s\n' "$1" >&2; exit 1; }

[ -n "${DEPLOY_SHA:-}" ] || fail "Falta DEPLOY_SHA: no sé qué commit desplegar."
export IMAGE_TAG="${IMAGE_TAG:-$DEPLOY_SHA}"

# --- Comprobaciones previas --------------------------------------------------
#
# Nada de esto es paranoia de más: en esta máquina hay una base de datos de
# producción de otro proyecto con dos meses de uptime.

log "Comprobando que no piso nada ajeno"

# 1. Ningún contenedor con nuestros nombres puede pertenecer a otro proyecto.
for nombre in accounting-postgres accounting-redis accounting-api accounting-web; do
  duenio="$(docker inspect "$nombre" \
    --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null || true)"
  if [ -n "$duenio" ] && [ "$duenio" != "$PROJECT" ]; then
    fail "El contenedor $nombre pertenece al proyecto '$duenio'. Parando antes de tocarlo."
  fi
done

# 2. Los puertos que vamos a publicar tienen que estar libres, o ya ser
#    nuestros (un redeploy normal).
# Se leen las dos variables sueltas, sin `source`. Bash y Docker no parsean un
# .env igual: `CORS_ORIGINS=["http://host:3001"]` sourceado en bash pierde las
# comillas y queda como JSON inválido, y al exportarse gana sobre el fichero en
# la interpolación de Compose. Lo pagamos con un arranque roto de la API.
leer_env() { [ -f "$APP_DIR/.env" ] && sed -n "s/^$1=//p" "$APP_DIR/.env" | tail -1; }
WEB_PORT="$(leer_env WEB_PORT)"
API_PORT="$(leer_env API_PORT)"
for puerto in "${WEB_PORT:-3000}" "${API_PORT:-8000}"; do
  en_uso="$(ss -tlnp 2>/dev/null | grep -E "[:.]${puerto} " || true)"
  if [ -n "$en_uso" ] && ! docker ps --filter "label=com.docker.compose.project=$PROJECT" \
       --format '{{.Ports}}' | grep -q ":${puerto}->"; then
    fail "El puerto $puerto ya está ocupado por otro proceso: $en_uso"
  fi
done

# 3. Disco. Sin margen, un `docker pull` a medias deja el disco lleno y el
#    Postgres del vecino sin poder escribir.
libre_mb="$(df -Pm / | awk 'NR==2 {print $4}')"
[ "$libre_mb" -ge 2048 ] || fail "Solo quedan ${libre_mb} MB libres en /. Se necesitan 2 GB."

# --- Código ------------------------------------------------------------------

log "Sincronizando el código en $APP_DIR"
# `git clone` no sirve: provision.sh ya dejó el .env ahí dentro y clone exige
# un directorio vacío. init + fetch da el mismo resultado sin esa condición.
if [ ! -d "$APP_DIR/.git" ]; then
  git init -q "$APP_DIR"
  git -C "$APP_DIR" remote add origin "$REPO_URL"
fi
cd "$APP_DIR"
git fetch --prune origin
# reset --hard, no merge: el servidor refleja el repo, nunca es origen de
# cambios. Si alguien editó a mano, se pierde, y eso es lo correcto.
git reset --hard "$DEPLOY_SHA"
git clean -fd

[ -f .env ] || fail "Falta $APP_DIR/.env — provision.sh debería haberlo creado."

# --- Imágenes ----------------------------------------------------------------

log "Obteniendo las imágenes ($IMAGE_TAG)"
# No se construye en el servidor: 3.7 GB de RAM compartidos con producción
# ajena. `pull_policy: missing` en el override evita bajar lo que ya está.
"${COMPOSE[@]}" pull --quiet api web 2>/dev/null || {
  # Si el registro no las tiene (o son privadas), sirve una imagen cargada a
  # mano con `docker load`. Si tampoco está, no hay nada que desplegar.
  for img in api web; do
    docker image inspect "ghcr.io/camiloarias12/accounting-$img:$IMAGE_TAG" >/dev/null 2>&1 \
      || fail "No encuentro la imagen de $img con tag $IMAGE_TAG, ni en el registro ni local."
  done
  log "Registro inaccesible; uso las imágenes que ya están en el servidor"
}

# --- Migraciones y arranque --------------------------------------------------

log "Aplicando migraciones"
# Con la imagen nueva y antes de cambiar los contenedores: si la migración
# falla, los viejos siguen sirviendo con el esquema viejo. `run` respeta
# depends_on, así que espera a que Postgres esté healthy.
"${COMPOSE[@]}" up -d postgres redis
# `run` no tiene --no-build (solo `up`); con la imagen ya presente
# y pull_policy: missing, no construye nada igualmente.
"${COMPOSE[@]}" run --rm api alembic upgrade head

log "Levantando los servicios"
"${COMPOSE[@]}" up -d --no-build --remove-orphans

log "Verificando que la API responda"
api_port="${API_PORT:-8000}"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${api_port}/api/v1/health" >/dev/null 2>&1; then
    log "Despliegue correcto: $(git rev-parse --short HEAD)"
    "${COMPOSE[@]}" ps
    # Solo nuestras imágenes sueltas: un prune global se llevaría las de
    # jorgedarek-app que sirven para hacerle rollback.
    docker image prune -f --filter "label=com.docker.compose.project=$PROJECT" >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 2
done

echo "La API no respondió tras 60s. Últimos logs:" >&2
"${COMPOSE[@]}" logs --tail 50 api >&2
exit 1
