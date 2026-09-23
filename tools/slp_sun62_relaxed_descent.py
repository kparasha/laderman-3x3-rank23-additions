#!/usr/bin/env python3
"""From Sun @62: all relaxed add_inter (+1) shells, bounded downhill hill each."""

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

from slp_relaxed_add_inter import add_inter_relaxed, total_cost  # noqa: E402
from slp_sun_gold_bfs import scheme_key  # noqa: E402
from slp_w_mutate import SIDES0, expand, matches_gold, mutate, write_best  # noqa: E402


def collect_shells(sides):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    shells = {}
    start_k = scheme_key(sides)
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
                    tot = total_cost(trial)
                    if tot < total_cost(sides):
                        continue
                    k = scheme_key(trial)
                    if k == start_k:
                        continue
                    shells.setdefault(k, trial)
    return list(shells.values())


def downhill(sides, golds, rounds, seed):
    rng = random.Random(seed)
    cur = deepcopy(sides)
    cur_t = total_cost(cur)
    best, best_t = deepcopy(cur), cur_t
    for _ in range(rounds):
        which = rng.choice(["U", "V", "W"])
        cand, _ = mutate(cur[which], golds[which], rng)
        if cand is None or not matches_gold(cand, golds[which]):
            continue
        trial = deepcopy(cur)
        trial[which] = cand
        tt = total_cost(trial)
        if tt < cur_t:
            cur, cur_t = trial, tt
            if tt < best_t:
                best, best_t = deepcopy(cur), tt
    return best, best_t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, default=Path("submissions/director-agentic-sun-cse-hill/sides.json"))
    ap.add_argument("--max-shells", type=int, default=20)
    ap.add_argument("--hill-rounds", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=760001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun62-relaxed-descent"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun62-relaxed-descent-cycle76.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}
    start_t = total_cost(start)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    shells = collect_shells(start)
    log(f"start={start_t} shells_at_plus1={len(shells)}")
    shells = shells[: args.max_shells]
    global_best = start_t
    global_sides = start
    for i, sh in enumerate(shells):
        best, bt = downhill(sh, golds, args.hill_rounds, args.seed + i * 17)
        if bt < global_best:
            global_best = bt
            global_sides = best
            log(f"shell {i+1} hill_best={bt}")

    write_best(
        args.out,
        global_sides["W"],
        global_sides["U"],
        global_sides["V"],
        {"note": "relaxed descent", "improved": global_best < 56},
    )
    summary = {
        "start_total": start_t,
        "shells_used": len(shells),
        "hill_rounds": args.hill_rounds,
        "best_total": global_best,
        "improved": global_best < 56,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if global_best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
