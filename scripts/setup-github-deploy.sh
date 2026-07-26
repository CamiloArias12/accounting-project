#!/usr/bin/env bash
#
# Configuración inicial del despliegue automático. Se ejecuta UNA vez, desde tu
# máquina, no desde CI:
#
#   ./scripts/setup-github-deploy.sh 46.224.38.172
#
# Hace lo único que GitHub Actions no puede hacer solo: darle al pipeline una
# credencial para entrar al servidor. Genera la clave, la instala (te va a pedir
# la contraseña de root una vez) y sube los tres secrets al repo con `gh`.
#
# A partir de aquí, cada push a main despliega sin intervención.

set -euo pipefail

HOST="${1:-}"
USER_REMOTO="${2:-root}"
KEY="$HOME/.ssh/accounting_deploy"

if [ -z "$HOST" ]; then
  echo "Uso: $0 <ip-del-servidor> [usuario]" >&2
  exit 1
fi

command -v gh >/dev/null || { echo "Falta el CLI de GitHub (gh)." >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh no está autenticado: corré 'gh auth login'." >&2; exit 1; }

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }

if [ -f "$KEY" ]; then
  log "La clave $KEY ya existe, se reutiliza"
else
  log "Generando la clave de despliegue"
  # Sin passphrase: el runner no tiene a nadie que la escriba.
  ssh-keygen -t ed25519 -C "github-actions-deploy" -f "$KEY" -N "" >/dev/null
fi

log "Instalando la clave pública en $USER_REMOTO@$HOST (te pedirá la contraseña)"
ssh-copy-id -i "$KEY.pub" "$USER_REMOTO@$HOST"

log "Comprobando que la clave funciona"
ssh -o BatchMode=yes -i "$KEY" "$USER_REMOTO@$HOST" 'echo "conexión OK: $(hostname)"'

log "Subiendo los secrets al repositorio"
gh secret set SSH_PRIVATE_KEY < "$KEY"
gh secret set DEPLOY_HOST --body "$HOST"
# Fija la identidad del servidor: sin esto, el workflow acepta la clave que le
# anuncien y un secuestro de la IP recibiría el deploy.
ssh-keyscan -H "$HOST" 2>/dev/null | gh secret set SSH_KNOWN_HOSTS
[ "$USER_REMOTO" != "root" ] && gh variable set DEPLOY_USER --body "$USER_REMOTO"

log "Listo. El próximo push a main despliega solo."
echo "Para lanzarlo ahora sin esperar: gh workflow run CI --ref main"
