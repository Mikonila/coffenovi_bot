#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".env" ]]; then
  echo ".env not found in project root."
  exit 1
fi

read_env_var() {
  local key="$1"
  python3 - "$key" .env <<'PY'
import sys
from pathlib import Path

key = sys.argv[1]
env_path = Path(sys.argv[2])

for raw_line in env_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    current_key, value = line.split("=", 1)
    if current_key.strip() != key:
        continue
    value = value.strip().strip('"').strip("'")
    print(value)
    break
PY
}

DEPLOY_HOST="${DEPLOY_HOST:-$(read_env_var DEPLOY_HOST)}"
DEPLOY_USER="${DEPLOY_USER:-$(read_env_var DEPLOY_USER)}"
DEPLOY_PATH="${DEPLOY_PATH:-$(read_env_var DEPLOY_PATH)}"
DEPLOY_SERVICE="${DEPLOY_SERVICE:-$(read_env_var DEPLOY_SERVICE)}"
DEPLOY_PORT="${DEPLOY_PORT:-$(read_env_var DEPLOY_PORT)}"
DEPLOY_PYTHON="${DEPLOY_PYTHON:-$(read_env_var DEPLOY_PYTHON)}"
DEPLOY_RUN_USER="${DEPLOY_RUN_USER:-$(read_env_var DEPLOY_RUN_USER)}"

if [[ -z "${DEPLOY_HOST:-}" || -z "${DEPLOY_USER:-}" || -z "${DEPLOY_PATH:-}" || -z "${DEPLOY_SERVICE:-}" ]]; then
  cat <<'EOF'
Add these variables to .env before deployment:

  DEPLOY_HOST=138.249.149.55
  DEPLOY_USER=root
  DEPLOY_PATH=/opt/coffee-novi-bot
  DEPLOY_SERVICE=coffee-novi-bot

Optional:
  DEPLOY_PORT=22
  DEPLOY_PYTHON=python3
  DEPLOY_RUN_USER=root
EOF
  exit 1
fi

DEPLOY_PORT="${DEPLOY_PORT:-22}"
DEPLOY_PYTHON="${DEPLOY_PYTHON:-python3}"
DEPLOY_RUN_USER="${DEPLOY_RUN_USER:-$DEPLOY_USER}"

SSH_TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"
RSYNC_RSH="ssh -p ${DEPLOY_PORT}"

echo "Uploading project to ${SSH_TARGET}:${DEPLOY_PATH}"

ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" "mkdir -p '${DEPLOY_PATH}/app' '${DEPLOY_PATH}/data'"

rsync -avz --delete -e "${RSYNC_RSH}" \
  ./app/ "${SSH_TARGET}:${DEPLOY_PATH}/app/"

rsync -avz -e "${RSYNC_RSH}" \
  ./requirements.txt \
  ./README.md \
  ./.env \
  ./"HercegNovi Standards.xlsx" \
  "${SSH_TARGET}:${DEPLOY_PATH}/"

if [[ -f "data/cloudinary_urls.json" ]]; then
  rsync -avz -e "${RSYNC_RSH}" \
    ./data/cloudinary_urls.json \
    "${SSH_TARGET}:${DEPLOY_PATH}/data/cloudinary_urls.json"
fi

echo "Installing dependencies on server"

ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" <<EOF
set -euo pipefail
cd "${DEPLOY_PATH}"
${DEPLOY_PYTHON} -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
EOF

echo "Installing systemd service ${DEPLOY_SERVICE}"
ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" <<EOF
set -euo pipefail
cat > /etc/systemd/system/${DEPLOY_SERVICE}.service <<SERVICE
[Unit]
Description=Coffee Novi Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${DEPLOY_RUN_USER}
WorkingDirectory=${DEPLOY_PATH}
ExecStart=${DEPLOY_PATH}/venv/bin/python -m app.bot
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable ${DEPLOY_SERVICE}
EOF

echo "Restarting service ${DEPLOY_SERVICE}"
ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" \
  "systemctl restart '${DEPLOY_SERVICE}' && systemctl status '${DEPLOY_SERVICE}' --no-pager --lines=20"

echo "Deploy completed."
