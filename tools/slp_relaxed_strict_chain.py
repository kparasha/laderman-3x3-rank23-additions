#!/usr/bin/env python3
"""Depth-2: one relaxed add_inter then one strict mutate; min total cost."""

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

from slp_relaxed_add_inter import add_inter_relaxed  # noqa: E402
from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import expand, matches_gold, mutate  # noqa: E402


def relaxed_step(start, golds, rng):
    name = rng.choice(("U", "V", "W"))
    _, vs = expand(start[name])
    n = len(vs)
    for _ in range(16):
        a, b = rng.randrange(n), rng.randrange(n)
        sign = rng.choice((1, -1))
        cand = add_inter_relaxed(start[name], golds[name], a, b, sign, 1)
        if cand is None:
            continue
        trial = deepcopy(start)
        trial[name] = cand
        if all(matches_gold(trial[k], golds[k]) for k in ("U", "V", "W")):
            return trial
    return start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", type=int, default=900)
    ap.add_argument("--seed", type=int, default=980001)
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-relaxed-strict-chain")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(start[n])[0] for n in ("U", "V", "W")}
    rng = random.Random(args.seed)
    t0 = time.time()
    best = total_cost(start)
    for _ in range(args.chains):
        mid = relaxed_step(start, golds, rng)
        name = rng.choice(("U", "V", "W"))
        cand, _ = mutate(mid[name], golds[name], rng)
        if cand is None or not matches_gold(cand, golds[name]):
            continue
        trial = deepcopy(mid)
        trial[name] = cand
        best = min(best, total_cost(trial))
    summary = {
        "start": total_cost(start),
        "best": best,
        "chains": args.chains,
        "improved": best < total_cost(start),
        "beats56": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
