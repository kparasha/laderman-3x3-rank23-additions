#!/usr/bin/env python3
"""Three consecutive flips from Stapleton; min compact rank when Brent=0."""

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=1000002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-rank-three-flip-stap")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    best_rank = len(base["u"])
    brent_hits = 0
    for _ in range(args.samples):
        cur = deepcopy(base)
        for _ in range(3):
            cur = flip(cur, rng)
        if brent_residual(cur["u"], cur["v"], cur["w"]) != 0:
            continue
        brent_hits += 1
        comp = compact_rank(cur)
        best_rank = min(best_rank, len(comp["u"]))
    summary = {
        "samples": args.samples,
        "brent_hits": brent_hits,
        "best_rank": best_rank,
        "improved": best_rank < 23,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
