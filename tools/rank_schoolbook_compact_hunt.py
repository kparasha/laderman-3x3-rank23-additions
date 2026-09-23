#!/usr/bin/env python3
"""Schoolbook walk; at Brent=0 track min compact rank (plus-heavy, 4.5k steps)."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from flipgraph_search import brent_residual, compact_rank, flip, plus, schoolbook  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=4500)
    ap.add_argument("--plus-prob", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=1260001)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-schoolbook-compact-hunt-126")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    cur = schoolbook()
    res = brent_residual(cur["u"], cur["v"], cur["w"])
    t0 = time.time()
    brent0 = 0
    best_rank = len(cur["u"])
    rank_at_brent0 = []
    for _ in range(args.steps):
        cand = plus(cur, rng) if rng.random() < args.plus_prob else flip(cur, rng)
        nr = brent_residual(cand["u"], cand["v"], cand["w"])
        if nr <= res or (nr == res + 1 and rng.random() < 0.015):
            cur, res = cand, nr
        if res == 0:
            brent0 += 1
            r = len(compact_rank(cur)["u"])
            rank_at_brent0.append(r)
            best_rank = min(best_rank, r)
            if r < 23:
                break
    summary = {
        "steps": args.steps,
        "plus_prob": args.plus_prob,
        "brent0_visits": brent0,
        "best_compact_rank": best_rank,
        "min_at_brent0": min(rank_at_brent0) if rank_at_brent0 else None,
        "improved": best_rank < 23,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
