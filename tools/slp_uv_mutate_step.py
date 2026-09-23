#!/usr/bin/env python3
"""One-step joint U+V side mutate proposals on SIDES0; accept if total cost drops."""

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
from slp_w_mutate import expand, matches_gold, mutate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposals", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=890001)
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-uv-mutate-step"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    rng = random.Random(args.seed)
    t0 = time.time()
    best = deepcopy(sides)
    best_c = total_cost(best)
    hits = 0
    for _ in range(args.proposals):
        trial = deepcopy(best)
        for name in ("U", "V"):
            cand, _ = mutate(trial[name], golds[name], rng)
            if cand is None or not matches_gold(cand, golds[name]):
                continue
            trial[name] = cand
        c = total_cost(trial)
        if c < best_c:
            hits += 1
            best_c = c
            best = trial
    summary = {
        "start": total_cost(sides),
        "best": best_c,
        "improving_proposals": hits,
        "proposals": args.proposals,
        "improved": best_c < total_cost(sides),
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_c < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
