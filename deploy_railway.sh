#!/usr/bin/env bash
set -euo pipefail

if ! command -v railway >/dev/null 2>&1; then
  cat <<'EOF'
Railway CLI is not installed.

Install it and log in first:
  npm install -g @railway/cli
  railway login
EOF
  exit 1
fi

if [[ ! -f "railway.toml" ]]; then
  echo "railway.toml not found in project root."
  exit 1
fi

if [[ ! -f "requirements.txt" || ! -f "HercegNovi Standards.xlsx" ]]; then
  echo "Project files are incomplete: requirements.txt and HercegNovi Standards.xlsx are required."
  exit 1
fi

cat <<'EOF'
Before first deploy, set these variables in Railway:

  BOT_TOKEN
  ADMIN_USER_IDS
  CLOUDINARY_CLOUD_NAME
  CLOUDINARY_API_KEY
  CLOUDINARY_API_SECRET
  AUTO_UPLOAD_TO_CLOUDINARY=true

Then link the project once:
  railway link

Starting Railway deploy...
EOF

railway up
