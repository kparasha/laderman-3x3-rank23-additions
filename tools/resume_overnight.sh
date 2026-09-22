#!/usr/bin/env bash
# Resume dual-track overnight jobs from local checkpoints (no network).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs/checkpoints \
  submissions/attempt017-w-affine submissions/attempt018-support \
  submissions/attempt016-w-cse submissions/attempt016-w-mutate

AFF_CK=logs/checkpoints/affine_checkpoint.json
SUP_CK=logs/checkpoints/support_checkpoint.json
CSE_CK=logs/checkpoints/cse_checkpoint.json
MUT_CK=logs/checkpoints/mutate_checkpoint.json

if [[ -f "$AFF_CK" ]]; then
  echo "Resuming affine/uv-mutate from $AFF_CK"
  nohup python3 -u tools/slp_w_affine.py \
    --resume "$AFF_CK" --trials 500000 --seed 11 --status-every 500 \
    --cse-seeds 1 --sterile-after 200000 --max-edits 2 \
    --log logs/w-affine-overnight.log --out submissions/attempt017-w-affine \
    >> logs/w-affine-overnight.stdout 2>&1 &
  echo $! > logs/checkpoints/affine.pid
  echo "affine pid $(cat logs/checkpoints/affine.pid)"
else
  echo "No affine checkpoint — skip"
fi

if [[ -f "$SUP_CK" ]]; then
  echo "Resuming support from $SUP_CK"
  nohup python3 -u tools/support_overnight.py \
    --resume "$SUP_CK" --edits 2000000 --seed 21 --status-every 20000 \
    --log logs/support-overnight.log --out submissions/attempt018-support \
    >> logs/support-overnight.stdout 2>&1 &
  echo $! > logs/checkpoints/support.pid
  echo "support pid $(cat logs/checkpoints/support.pid)"
else
  echo "No support checkpoint — skip"
fi

# Legacy (optional)
if [[ -f "$CSE_CK" ]]; then
  echo "(legacy) CSE checkpoint present at $CSE_CK — not auto-resumed (neighborhood sterile)"
fi
if [[ -f "$MUT_CK" ]]; then
  echo "(legacy) mutate checkpoint present at $MUT_CK — not auto-resumed (exhausted)"
fi
