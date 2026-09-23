#!/usr/bin/env python3
"""Schoolbook flip-walk; track min support among Brent rank-23 states."""

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
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=960003)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-flipgraph-support-hunt"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    cur = schoolbook()
    res = 0
    best_s = 10**9
    rank23_seen = 0
    t0 = time.time()
    for _ in range(args.steps):
        cand = plus(cur, rng) if rng.random() < 0.04 else flip(cur, rng)
        nr = brent_residual(cand["u"], cand["v"], cand["w"])
        if nr <= res or rng.random() < 0.012:
            cur, res = cand, nr
            if res == 0:
                c = compact_rank(cur)
                if len(c["u"]) == 23:
                    rank23_seen += 1
                    s = support(c)
                    best_s = min(best_s, s)
    summary = {
        "steps": args.steps,
        "rank23_seen": rank23_seen,
        "best_support_rank23": best_s if rank23_seen else None,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
