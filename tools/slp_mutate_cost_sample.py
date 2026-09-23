#!/usr/bin/env python3
"""Sample strict side mutates; min total_cost per start certificate."""

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


def probe(sides, samples, seed):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    rng = random.Random(seed)
    start = total_cost(sides)
    best = start
    for _ in range(samples):
        name = rng.choice(("U", "V", "W"))
        cand, _ = mutate(deepcopy(sides)[name], golds[name], rng)
        if cand is None or not matches_gold(cand, golds[name]):
            continue
        trial = deepcopy(sides)
        trial[name] = cand
        best = min(best, total_cost(trial))
    return start, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=960002)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-mutate-cost-sample"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out = {}
    for label, path in (
        ("at56", Path("submissions/_sun_sides0.json")),
        ("at62", Path("submissions/director-agentic-sun-cse-hill/sides.json")),
    ):
        sides = json.loads(path.read_text(encoding="utf-8"))
        off = 0 if label == "at56" else 17
        s, b = probe(sides, args.samples, args.seed + off)
        out[label] = {"start": s, "min_sampled": b}
    summary = {
        "samples": args.samples,
        "results": out,
        "beats56": out.get("at56", {}).get("min_sampled", 56) < 56
        or out.get("at62", {}).get("min_sampled", 62) < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["beats56"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
