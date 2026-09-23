#!/usr/bin/env python3
"""Random pair-zero samples on Stapleton then exhaustive_zero."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from copy import deepcopy
from itertools import combinations
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from support_overnight import brent_ok, exhaustive_zero, getv, mats, positions, setv, support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=870004)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-pair-zero-sample"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    pos = list(positions(*mats(base)))
    pairs = list(combinations(pos, 2))
    rng = random.Random(args.seed)
    t0 = time.time()
    start = support(*mats(base))
    best = start
    hits = 0
    for _ in range(min(args.samples, len(pairs))):
        p1, p2 = rng.choice(pairs)
        trial = deepcopy(base)
        for p in (p1, p2):
            if getv(trial, *p) != 0:
                setv(trial, *p, 0)
        if not brent_ok(*mats(trial)):
            continue
        hits += 1
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best:
            best = s
    summary = {
        "start_support": start,
        "best_support": best,
        "brent_pair_hits": hits,
        "samples": args.samples,
        "improved": best < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
