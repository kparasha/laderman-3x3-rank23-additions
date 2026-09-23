#!/usr/bin/env python3
"""Random 3-flip samples from Stapleton; min lifted support among Brent=0 hits."""

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


def support_of(data):
    lifted, _ = exhaustive_zero(deepcopy(data))
    return count_support(*mats(lifted))


def three_flip(base, rng):
    d = base
    for _ in range(3):
        d = flip(d, rng)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=1600)
    ap.add_argument("--seed", type=int, default=1180002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-support-three-flip-sample-118")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    start_s = support_of(base)
    best_s = start_s
    brent_hits = 0
    for _ in range(args.samples):
        trial = three_flip(base, rng)
        if brent_residual(trial["u"], trial["v"], trial["w"]) != 0:
            continue
        brent_hits += 1
        best_s = min(best_s, support_of(trial))
        if best_s < 152:
            (args.out / "solution.json").write_text(json.dumps(trial, indent=2), encoding="utf-8")
            break
    summary = {
        "samples": args.samples,
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
