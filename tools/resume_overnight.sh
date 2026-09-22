#!/usr/bin/env bash
# Resume / relaunch overnight research director (no network).
# Legacy dual-track affine/support only resume if checkpoints exist AND director is not preferred.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs/checkpoints \
  submissions/attempt017-w-affine submissions/attempt018-support \
  submissions/attempt016-w-cse submissions/attempt016-w-mutate

# Prefer the auto-research director (picks pending strategies from tools/strategies.json)
if pgrep -f "tools/research_director.py" >/dev/null 2>&1; then
  echo "research_director already running:"
  pgrep -fl "tools/research_director.py" || true
  exit 0
fi

echo "Launching research_director (max-cycles=30 timeout=1800s)"
nohup python3 -u tools/research_director.py --max-cycles 30 --timeout 1800 \
  >> logs/director-overnight.stdout 2>&1 &
echo $! > logs/checkpoints/director.pid
echo "director pid $(cat logs/checkpoints/director.pid)"
echo "tail -f logs/director.log logs/experiments.jsonl"
