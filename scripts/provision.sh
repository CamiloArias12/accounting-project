#!/usr/bin/env bash
#
# Deja el servidor listo para recibir un despliegue: Docker instalado, el
# directorio de la app creado y un .env válido. Lo ejecuta el workflow en cada
# deploy, antes de scripts/deploy.sh.
#
# Todo es idempotente: en un servidor ya aprovisionado no hace nada y termina
# en un par de segundos. Pensado para Debian/Ubuntu.

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/accounting-project}"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }

# --- Docker -----------------------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
  log "Instalando Docker"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg openssl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  # La distro se detecta sola: el repo de Docker es distinto en Debian y Ubuntu.
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "Docker ya está instalado: $(docker --version)"
fi

# El plugin de compose puede faltar en instalaciones viejas hechas a mano.
if ! docker compose version >/dev/null 2>&1; then
  log "Instalando el plugin de Docker Compose"
  apt-get install -y -qq docker-compose-plugin
fi

# --- Directorio de la aplicación --------------------------------------------

mkdir -p "$APP_DIR"

# --- .env --------------------------------------------------------------------

# Se genera UNA sola vez. Regenerarlo en cada deploy rompería dos cosas: la
# contraseña de Postgres ya quedó grabada en el volumen la primera vez, y
# rotar JWT_SECRET invalida las sesiones de todo el mundo en cada push.
if [ ! -f "$APP_DIR/.env" ]; then
  log "Generando $APP_DIR/.env con credenciales aleatorias"
  umask 077
  cat > "$APP_DIR/.env" <<EOF
# Generado por scripts/provision.sh en el primer despliegue.
# Para rotar una credencial: editar aquí y volver a desplegar. Cambiar
# POSTGRES_PASSWORD exige además actualizarla dentro de Postgres, porque el
# volumen conserva la que se usó al inicializarse.
ENVIRONMENT=production

# Puertos corridos: el servidor es compartido y 3000/8000 pueden estar en uso
# por el otro proyecto. La API escucha solo en loopback — la web la alcanza por
# la red interna de Compose, nadie más necesita llegarle.
WEB_PORT=${WEB_PORT:-3001}
WEB_BIND=0.0.0.0
API_PORT=${API_PORT:-8001}
API_BIND=127.0.0.1

POSTGRES_USER=accounting
POSTGRES_PASSWORD=$(openssl rand -hex 24)
POSTGRES_DB=accounting

JWT_SECRET=$(openssl rand -hex 32)

DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
CACHE_TTL_SECONDS=300

CORS_ORIGINS=["http://${DEPLOY_HOST:-localhost}:${WEB_PORT:-3001}"]
EOF
  chmod 600 "$APP_DIR/.env"
else
  log ".env ya existe, se conserva"
fi

# --- Firewall ----------------------------------------------------------------

# Solo el puerto de la web, y solo si ufw ya está activo. No se activa aquí:
# encender un firewall por sorpresa en un servidor remoto es la forma clásica
# de perder el acceso SSH. La API no se abre: escucha en loopback.
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  log "Abriendo el puerto de la web en ufw"
  ufw allow "${WEB_PORT:-3001}/tcp" >/dev/null
fi

log "Servidor listo"
