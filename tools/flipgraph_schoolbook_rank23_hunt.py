#!/usr/bin/env python3
"""Schoolbook walk with high SA accept; stop when rank-23 seen, report min support."""

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
    ap.add_argument("--steps", type=int, default=5500)
    ap.add_argument("--plus-prob", type=float, default=0.06)
    ap.add_argument("--seed", type=int, default=1090002)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-schoolbook-rank23-hunt")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    cur = schoolbook()
    res = brent_residual(cur["u"], cur["v"], cur["w"])
    rank23_seen = 0
    best_s = 10**9
    t0 = time.time()
    for _ in range(args.steps):
        cand = plus(cur, rng) if rng.random() < args.plus_prob else flip(cur, rng)
        nr = brent_residual(cand["u"], cand["v"], cand["w"])
        if nr <= res or rng.random() < 0.025:
            cur, res = cand, nr
            if res == 0:
                comp = compact_rank(cur)
                if len(comp["u"]) == 23:
                    rank23_seen += 1
                    best_s = min(best_s, support(comp))
    summary = {
        "steps": args.steps,
        "rank23_seen": rank23_seen,
        "best_support_rank23": best_s if rank23_seen else None,
        "improved": rank23_seen > 0 and best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
