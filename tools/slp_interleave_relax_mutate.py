#!/usr/bin/env python3
"""Random interleaved relaxed add_inter + strict mutate walks from Sun @62."""

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
from slp_w_mutate import expand, matches_gold, mutate, write_best  # noqa: E402


def step_relaxed(cur, golds, rng):
    name = rng.choice(("U", "V", "W"))
    _, vs = expand(cur[name])
    n = len(vs)
    c0 = total_cost(cur)
    for _ in range(12):
        a, b = rng.randrange(n), rng.randrange(n)
        sign = rng.choice((1, -1))
        cand = add_inter_relaxed(cur[name], golds[name], a, b, sign, 1)
        if cand is None:
            continue
        trial = deepcopy(cur)
        trial[name] = cand
        if total_cost(trial) <= c0:
            return trial, True
    return cur, False


def step_mutate(cur, golds, rng):
    name = rng.choice(("U", "V", "W"))
    side_new, _ = mutate(cur[name], golds[name], rng)
    if side_new is None or not matches_gold(side_new, golds[name]):
        return cur, False
    trial = deepcopy(cur)
    trial[name] = side_new
    if total_cost(trial) < total_cost(cur):
        return trial, True
    return cur, False


def walk(start, steps, seed):
    rng = random.Random(seed)
    golds = {n: expand(start[n])[0] for n in ("U", "V", "W")}
    cur = deepcopy(start)
    best_c = total_cost(cur)
    best = deepcopy(cur)
    for _ in range(steps):
        if rng.random() < 0.45:
            cur, _ = step_relaxed(cur, golds, rng)
        else:
            cur, _ = step_mutate(cur, golds, rng)
        c = total_cost(cur)
        if c < best_c:
            best_c = c
            best = deepcopy(cur)
    return best_c, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--walks", type=int, default=48)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--seed", type=int, default=850001)
    ap.add_argument(
        "--sides", type=Path, default=Path("submissions/director-agentic-sun-cse-hill/sides.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-interleave-relax-mutate")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides.read_text(encoding="utf-8"))
    t0 = time.time()
    global_best = total_cost(start)
    global_side = start
    for w in range(args.walks):
        c, best = walk(start, args.steps, args.seed + w * 9973)
        if c < global_best:
            global_best = c
            global_side = best

    summary = {
        "start_cost": total_cost(start),
        "walks": args.walks,
        "steps_per_walk": args.steps,
        "best_cost": global_best,
        "beats56": global_best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if global_best < 56:
        write_best(args.out, global_side["W"], global_side["U"], global_side["V"], {"note": "interleave"})
    return 0 if global_best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
