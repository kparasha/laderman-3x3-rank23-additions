#!/usr/bin/env python3
"""Greedy hill on one side (U, V, or W) of a fixed sides certificate."""

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
from slp_w_mutate import expand, matches_gold, mutate, write_best  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=("U", "V", "W"), default="U")
    ap.add_argument("--rounds", type=int, default=1800)
    ap.add_argument("--seed", type=int, default=870003)
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-u-only-hill"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    rng = random.Random(args.seed)
    cur = deepcopy(sides)
    best_c = total_cost(cur)
    t0 = time.time()
    for _ in range(args.rounds):
        cand, _ = mutate(cur[args.side], golds[args.side], rng)
        if cand is None or not matches_gold(cand, golds[args.side]):
            continue
        trial = deepcopy(cur)
        trial[args.side] = cand
        c = total_cost(trial)
        if c < best_c:
            best_c = c
            cur = trial
    summary = {
        "side": args.side,
        "start": total_cost(sides),
        "best": best_c,
        "improved": best_c < total_cost(sides),
        "beats56": best_c < 56,
        "rounds": args.rounds,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_c < 56:
        write_best(args.out, cur["W"], cur["U"], cur["V"], {"note": f"{args.side}-only hill"})
    return 0 if best_c < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
