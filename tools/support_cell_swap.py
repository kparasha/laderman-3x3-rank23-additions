#!/usr/bin/env python3
"""Exhaustive pairwise value-swap on Stapleton nonzero cells (not random reassign).

Two-cell reassign picks independent new ternaries; swapping values may hit a
different Brent-feasible manifold and lower support after greedy zeroing.

  python3 -u tools/support_cell_swap.py --max-pairs 12000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from itertools import combinations
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from support_overnight import (  # noqa: E402
    brent_ok,
    exhaustive_zero,
    getv,
    mats,
    orbit_seeds,
    positions,
    setv,
    support,
    write_out,
)


def swap_cells(data, p1, p2):
    trial = deepcopy(data)
    v1 = getv(trial, *p1)
    v2 = getv(trial, *p2)
    setv(trial, *p1, v2)
    setv(trial, *p2, v1)
    return trial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--max-pairs", type=int, default=12_000, help="Cap pair trials (0 = all)")
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-cell-swap"))
    ap.add_argument("--log", type=Path, default=Path("logs/cell-swap-cycle64.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    orb = orbit_seeds(base)
    orb.sort(key=lambda x: x[0])
    best, _ = exhaustive_zero(deepcopy(orb[0][2]))
    start_s = support(*mats(best))
    pos = positions(*mats(best))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    pairs = []
    for p1, p2 in combinations(pos, 2):
        if getv(best, *p1) == getv(best, *p2):
            continue
        pairs.append((p1, p2))
    if args.max_pairs and len(pairs) > args.max_pairs:
        pairs = pairs[: args.max_pairs]

    log(f"start support={start_s} cells={len(pos)} swap_pairs={len(pairs)}")
    t0 = time.time()
    brent_hits = 0
    best_s = start_s
    best_data = best

    for n, (p1, p2) in enumerate(pairs, 1):
        trial = swap_cells(best_data, p1, p2)
        if not brent_ok(*mats(trial)):
            continue
        brent_hits += 1
        lifted, _ = exhaustive_zero(trial)
        s = support(*mats(lifted))
        if s < best_s:
            best_s = s
            best_data = lifted
            log(f"IMPROVED pair={n} support={s} {p1}<->{p2}")
            write_out(args.out, best_data, {"pair": [p1, p2], "improved": True})

    summary = {
        "start_support": start_s,
        "best_support": best_s,
        "improved": best_s < 152,
        "pairs_tried": len(pairs),
        "brent_hits": brent_hits,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
