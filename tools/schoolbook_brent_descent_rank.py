#!/usr/bin/env python3
"""Schoolbook walk prioritizing Brent residual decrease; track min compact rank."""

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

from flipgraph_search import brent_residual, compact_rank, flip, plus, schoolbook, support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=5000)
    ap.add_argument("--plus-prob", type=float, default=0.07)
    ap.add_argument("--seed", type=int, default=1140001)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-schoolbook-brent-descent")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    cur = schoolbook()
    res = brent_residual(cur["u"], cur["v"], cur["w"])
    best_rank = len(cur["u"])
    brent0 = 0
    best_sup_at23 = 10**9
    t0 = time.time()
    for _ in range(args.steps):
        cand = plus(cur, rng) if rng.random() < args.plus_prob else flip(cur, rng)
        nr = brent_residual(cand["u"], cand["v"], cand["w"])
        if nr < res or (nr == res and rng.random() < 0.008) or (nr > res and rng.random() < 0.002):
            cur, res = cand, nr
        if res == 0:
            brent0 += 1
            comp = compact_rank(cur)
            r = len(comp["u"])
            best_rank = min(best_rank, r)
            if r == 23:
                best_sup_at23 = min(best_sup_at23, support(comp))
            if r < 23:
                break
    summary = {
        "steps": args.steps,
        "brent0_visits": brent0,
        "best_rank": best_rank,
        "best_support_if_rank23": best_sup_at23 if best_sup_at23 < 10**9 else None,
        "improved_rank": best_rank < 23,
        "improved_support": best_sup_at23 < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved_rank"] or summary["improved_support"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
