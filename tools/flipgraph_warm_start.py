#!/usr/bin/env python3
"""Flip-graph random walk warm-started from a rank-23 solution; track min support."""

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
    ap.add_argument("--steps", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=820002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-flipgraph-warm")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cur = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    best_s = support(cur)
    best = deepcopy(cur)
    rank23_hits = 0

    for _ in range(args.steps):
        trial = flip(cur, rng)
        bad = brent_residual(trial["u"], trial["v"], trial["w"])
        if bad == 0:
            cur = trial
        elif bad < brent_residual(cur["u"], cur["v"], cur["w"]):
            cur = trial
        comp = compact_rank(cur)
        if len(comp["u"]) == 23 and brent_residual(comp["u"], comp["v"], comp["w"]) == 0:
            rank23_hits += 1
            s = support(comp)
            if s < best_s:
                best_s = s
                best = comp

    summary = {
        "steps": args.steps,
        "start_support": support(json.loads(args.src.read_text(encoding="utf-8"))),
        "best_support": best_s,
        "rank23_hits": rank23_hits,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_s < 152:
        (args.out / "solution.json").write_text(
            json.dumps(best, separators=(",", ":")), encoding="utf-8"
        )
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
