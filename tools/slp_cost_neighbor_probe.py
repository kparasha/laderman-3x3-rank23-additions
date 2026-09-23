#!/usr/bin/env python3
"""Random mutate samples: min certified total among gold-preserving neighbors."""

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

from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import SIDES0, expand, matches_gold, mutate  # noqa: E402


def probe(sides, samples, seed):
    golds = {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}
    rng = random.Random(seed)
    start = total_cost(sides)
    best = start
    for _ in range(samples):
        name = rng.choice(["U", "V", "W"])
        cand, _ = mutate(sides[name], golds[name], rng)
        if cand is None or not matches_gold(cand, golds[name]):
            continue
        trial = deepcopy(sides)
        trial[name] = cand
        best = min(best, total_cost(trial))
    return start, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=800001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-cost-neighbor"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sides56 = {"U": SIDES0["U"], "V": SIDES0["V"], "W": SIDES0["W"]}
    sides62 = json.loads(
        Path("submissions/director-agentic-sun-cse-hill/sides.json").read_text(encoding="utf-8")
    )
    t0 = time.time()
    s56, b56 = probe(sides56, args.samples, args.seed)
    s62, b62 = probe(sides62, args.samples, args.seed + 1)
    summary = {
        "samples": args.samples,
        "at56": {"start": s56, "min_neighbor": b56},
        "at62": {"start": s62, "min_neighbor": b62},
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if b56 < 56 or b62 < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
