#!/usr/bin/env python3
"""From relaxed add_inter portals, greedy strict mutate — can @56 reach total <56?"""

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
from slp_sun_gold_bfs import scheme_key  # noqa: E402
from slp_w_mutate import expand, matches_gold, mutate, write_best  # noqa: E402


def enum_portals(sides, max_portals: int):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    seen = {scheme_key(sides): (total_cost(sides), deepcopy(sides))}
    for name in ("U", "V", "W"):
        _, vs = expand(sides[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    cand = add_inter_relaxed(sides[name], golds[name], a, b, sign, 1)
                    if cand is None:
                        continue
                    trial = deepcopy(sides)
                    trial[name] = cand
                    if not all(matches_gold(trial[k], golds[k]) for k in ("U", "V", "W")):
                        continue
                    k = scheme_key(trial)
                    if k not in seen:
                        seen[k] = (total_cost(trial), trial)
                    if len(seen) >= max_portals + 1:
                        break
                if len(seen) >= max_portals + 1:
                    break
            if len(seen) >= max_portals + 1:
                break
    base_k = scheme_key(sides)
    out = [v for kk, v in seen.items() if kk != base_k]
    return len(seen) - 1, out


def hill(sides, golds, rounds, rng):
    cur = deepcopy(sides)
    best_c = total_cost(cur)
    best = deepcopy(cur)
    for _ in range(rounds):
        name = rng.choice(("U", "V", "W"))
        side_new, _op = mutate(cur[name], golds[name], rng)
        if side_new is None or not matches_gold(side_new, golds[name]):
            continue
        trial = deepcopy(cur)
        trial[name] = side_new
        c = total_cost(trial)
        if c < best_c:
            best_c = c
            best = trial
            cur = trial
    return best_c, best


def run_start(sides, rounds, max_portals, seed):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    rng = random.Random(seed)
    start_c = total_cost(sides)
    n_portals, portals = enum_portals(sides, max_portals)
    global_best = start_c
    global_side = deepcopy(sides)
    for cost0, portal in portals:
        c, best = hill(portal, golds, rounds, rng)
        if c < global_best:
            global_best = c
            global_side = best
    c0, best0 = hill(sides, golds, rounds, rng)
    if c0 < global_best:
        global_best = c0
        global_side = best0
    return {
        "start_cost": start_c,
        "portals": n_portals,
        "best_cost": global_best,
        "improved": global_best < start_c,
    }, global_side


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=220)
    ap.add_argument("--max-portals", type=int, default=40)
    ap.add_argument("--seed", type=int, default=830001)
    ap.add_argument("--sides56", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument(
        "--sides62", type=Path, default=Path("submissions/director-agentic-sun-cse-hill/sides.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-relax-then-mutate")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    s56 = json.loads(args.sides56.read_text(encoding="utf-8"))
    r56, best56 = run_start(s56, args.rounds, args.max_portals, args.seed)
    r62 = None
    if args.sides62.exists():
        s62 = json.loads(args.sides62.read_text(encoding="utf-8"))
        r62, _ = run_start(s62, args.rounds, args.max_portals, args.seed + 1)

    summary = {
        "at56": r56,
        "at62": r62,
        "global_best": min(r56["best_cost"], r62["best_cost"] if r62 else 10**9),
        "beats56": r56["best_cost"] < 56 or (r62 and r62["best_cost"] < 56),
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if r56["best_cost"] < 56:
        write_best(args.out, best56["W"], best56["U"], best56["V"], {"from": "@56"})
    return 0 if summary["beats56"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
