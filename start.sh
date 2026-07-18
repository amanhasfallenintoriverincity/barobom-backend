#!/bin/bash
cd ~/barobom-backend
export PATH="$HOME/.local/bin:$PATH"
source .venv/bin/activate
set -a && source .env && set +a
exec python -m uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --log-level info
