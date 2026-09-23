#!/usr/bin/env python3
"""Random single flips on Stapleton; after compact, hunt rank<23 with Brent=0."""

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

from flipgraph_search import brent_residual, compact_rank, flip, support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3500)
    ap.add_argument("--seed", type=int, default=970001)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-flip-stap"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    best_rank = len(base["u"])
    best_sup = support(base)
    hits_brent0 = 0
    cur = deepcopy(base)
    for _ in range(args.steps):
        trial = flip(cur, rng)
        if brent_residual(trial["u"], trial["v"], trial["w"]) == 0:
            hits_brent0 += 1
            cur = trial
            comp = compact_rank(cur)
            r = len(comp["u"])
            if r < best_rank:
                best_rank = r
                best_sup = support(comp)
            if r < 23:
                break
    summary = {
        "steps": args.steps,
        "start_rank": len(base["u"]),
        "best_rank": best_rank,
        "best_support_at_best_rank": best_sup,
        "brent0_flips": hits_brent0,
        "improved": best_rank < 23,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
