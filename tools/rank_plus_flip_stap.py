#!/usr/bin/env python3
"""Stapleton + random plus term; flip walk; min compact rank when Brent=0."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from flipgraph_search import brent_residual, compact_rank, flip  # noqa: E402


def plus_term(data, rng):
    d = deepcopy(data)
    d["u"].append([rng.choice([-1, 0, 1]) for _ in range(9)])
    d["v"].append([rng.choice([-1, 0, 1]) for _ in range(9)])
    d["w"].append([rng.choice([-1, 0, 1]) for _ in range(9)])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--walks", type=int, default=55)
    ap.add_argument("--steps", type=int, default=95)
    ap.add_argument("--seed", type=int, default=1270001)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-plus-flip-stap-127"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    best_rank = len(base["u"])
    brent0_end = 0
    for w in range(args.walks):
        cur = plus_term(base, rng)
        res = brent_residual(cur["u"], cur["v"], cur["w"])
        for _ in range(args.steps):
            cand = flip(cur, rng)
            nr = brent_residual(cand["u"], cand["v"], cand["w"])
            if nr <= res or rng.random() < 0.025:
                cur, res = cand, nr
        if res == 0:
            brent0_end += 1
            r = len(compact_rank(cur)["u"])
            best_rank = min(best_rank, r)
            if r < 23:
                break
    summary = {
        "walks": args.walks,
        "steps_per_walk": args.steps,
        "brent0_end_walks": brent0_end,
        "best_rank": best_rank,
        "improved": best_rank < 23,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
