#!/usr/bin/env bash
# Unattended local Agentic Director (Cursor SDK) with macOS stay-awake.
# Keep the Mac on AC power overnight. Requires CURSOR_API_KEY in env or .env
# (loaded by agentic_director.py — this script does not source .env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs/checkpoints

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Missing .venv. Run: uv venv .venv --python 3.12 && uv pip install -r requirements.txt"
  exit 1
fi

# Presence check only (director loads .env itself; do not source secrets here)
if ! "$PY" -c "
from pathlib import Path
import os
ok = bool(os.environ.get('CURSOR_API_KEY', '').strip())
p = Path('.env')
if p.exists():
    for line in p.read_text().splitlines():
        s = line.strip()
        if s.startswith('CURSOR_API_KEY='):
            v = s.split('=', 1)[1].strip().strip('\"').strip(\"'\")
            if v:
                ok = True
print('ok' if ok else 'missing')
" | grep -q '^ok$'; then
  echo "CURSOR_API_KEY missing. Put it in .env (see .env.example) or export it."
  echo "Create a key at https://cursor.com/dashboard/integrations"
  exit 1
fi

if pgrep -f "tools/agentic_director.py" >/dev/null 2>&1; then
  echo "agentic_director already running:"
  pgrep -fl "tools/agentic_director.py" || true
  exit 0
fi

echo "Starting Unattended Local Agentic Search (caffeinate -i -s)"
# -i idle sleep; -s system sleep on AC power
# Base 3600s + adaptive budget (tight/wrap/extend) up to --timeout-max 5400s
nohup caffeinate -i -s "$PY" -u tools/agentic_director.py \
  --max-cycles 20 --timeout 3600 --timeout-max 5400 \
  >> logs/director-overnight.stdout 2>&1 &
echo $! > logs/checkpoints/director.pid
echo "pid $(cat logs/checkpoints/director.pid) — keep Mac on AC"
echo "tail -f logs/director.log logs/experiments.jsonl"
