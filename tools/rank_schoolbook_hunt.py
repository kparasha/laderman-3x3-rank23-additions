#!/usr/bin/env python3
"""Smoke flip-walk from schoolbook rank-27 toward rank<23."""

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
    ap.add_argument("--steps", type=int, default=3500)
    ap.add_argument("--seed", type=int, default=870002)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-schoolbook-rank-hunt"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    cur = schoolbook()
    res = 0
    best_lt23 = None
    t0 = time.time()
    for step in range(args.steps):
        cand = plus(cur, rng) if rng.random() < 0.04 else flip(cur, rng)
        new_res = brent_residual(cand["u"], cand["v"], cand["w"])
        if new_res <= res or rng.random() < 0.015:
            cur = cand
            res = new_res
            if res == 0:
                c = compact_rank(cur)
                r = len(c["u"])
                if r < 23:
                    best_lt23 = (r, support(c), step)
                    break
    summary = {
        "steps": args.steps,
        "best_lt23": best_lt23,
        "improved": best_lt23 is not None,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_lt23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
