#!/usr/bin/env python3
"""Flip+plus walk from Stapleton; min compact support among Brent rank-23 hits."""

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

from flipgraph_search import brent_residual, compact_rank, flip, plus, support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3500)
    ap.add_argument("--seed", type=int, default=990002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("submissions/director-agentic-flipgraph-stap-plus"),
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cur = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    res = brent_residual(cur["u"], cur["v"], cur["w"])
    best_s = support(cur)
    best_comp = None
    rank23_seen = 0
    for _ in range(args.steps):
        cand = plus(cur, rng) if rng.random() < 0.05 else flip(cur, rng)
        nr = brent_residual(cand["u"], cand["v"], cand["w"])
        if nr <= res or rng.random() < 0.01:
            cur, res = cand, nr
            if res == 0:
                comp = compact_rank(cur)
                if len(comp["u"]) == 23:
                    rank23_seen += 1
                    s = support(comp)
                    if s < best_s:
                        best_s = s
                        best_comp = comp
    summary = {
        "steps": args.steps,
        "rank23_seen": rank23_seen,
        "best_support": best_s,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_comp is not None:
        (args.out / "best_support.json").write_text(
            json.dumps(best_comp, indent=2), encoding="utf-8"
        )
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
