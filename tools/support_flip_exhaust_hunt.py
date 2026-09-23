#!/usr/bin/env python3
"""Stapleton flip walk; after Brent=0 apply exhaustive_zero (no pre-compact)."""

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

from flipgraph_search import brent_residual, flip  # noqa: E402
from support_overnight import exhaustive_zero, mats  # noqa: E402
from support_overnight import support as count_support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=1050002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-flip-exhaust-support")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cur = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    start_s = count_support(*mats(cur))
    best_s = start_s
    brent_hits = 0
    for _ in range(args.steps):
        trial = flip(cur, rng)
        if brent_residual(trial["u"], trial["v"], trial["w"]) != 0:
            continue
        brent_hits += 1
        cur = trial
        lifted, _ = exhaustive_zero(deepcopy(cur))
        s = count_support(*mats(lifted))
        if s < best_s:
            best_s = s
    summary = {
        "steps": args.steps,
        "start_support": start_s,
        "best_support": best_s,
        "brent_hits": brent_hits,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
