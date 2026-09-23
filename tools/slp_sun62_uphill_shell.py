#!/usr/bin/env python3
"""From Sun gold @62, enumerate cost-63 shells then downhill-only sides hill.

Single-step mutates are flat @62; one add_inter uphill may open a basin that
descends below 62 (not tested by flat SA or same-cost BFS).

  python3 -u tools/slp_sun62_uphill_shell.py \\
      submissions/director-agentic-sun-cse-hill/sides.json \\
      --uphill-trials 60000 --hill-rounds 12000 --max-shells 25
"""

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
from slp_sun_gold_bfs import scheme_key  # noqa: E402
from slp_w_mutate import SIDES0, cost, expand, matches_gold, mutate, write_best  # noqa: E402


def downhill_hill(start, golds, rounds, seed):
    rng = random.Random(seed)
    cur = deepcopy(start)
    cur_t = total_cost(cur)
    best = deepcopy(cur)
    best_t = cur_t
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
    ap.add_argument("sides_path", type=Path)
    ap.add_argument("--uphill-trials", type=int, default=60_000)
    ap.add_argument("--hill-rounds", type=int, default=12_000)
    ap.add_argument("--max-shells", type=int, default=25)
    ap.add_argument("--seed", type=int, default=650001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun62-uphill-shell"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun62-uphill-shell-cycle65.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides_path.read_text(encoding="utf-8"))
    golds = {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}
    start_t = total_cost(start)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start total={start_t} uphill_trials={args.uphill_trials} "
        f"hill_rounds={args.hill_rounds} max_shells={args.max_shells}"
    )
    t0 = time.time()
    rng = random.Random(args.seed)
    shells = {}
    cur = deepcopy(start)
    cur_t = start_t
    for _ in range(args.uphill_trials):
        which = rng.choice(["U", "V", "W"])
        cand, op = mutate(cur[which], golds[which], rng)
        if cand is None or not matches_gold(cand, golds[which]):
            continue
        trial = deepcopy(cur)
        trial[which] = cand
        tt = total_cost(trial)
        if tt == cur_t + 1:
            k = scheme_key(trial)
            shells.setdefault(k, (deepcopy(trial), op, which))

    log(f"found cost={cur_t + 1} shells={len(shells)} elapsed={time.time()-t0:.1f}s")
    global_best = start_t
    global_sides = start
    shell_items = list(shells.items())[: args.max_shells]
    for i, (k, (shell, op, which)) in enumerate(shell_items):
        best, bt = downhill_hill(shell, golds, args.hill_rounds, args.seed + 1000 + i)
        log(f"shell {i+1}/{len(shell_items)} op={which}/{op} hill_best={bt}")
        if bt < global_best:
            global_best = bt
            global_sides = best

    write_best(
        args.out,
        global_sides["W"],
        global_sides["U"],
        global_sides["V"],
        {"note": "uphill-shell best", "improved": global_best < 56},
    )
    summary = {
        "start_total": start_t,
        "shells_at_plus1": len(shells),
        "shells_hilled": len(shell_items),
        "best_total": global_best,
        "improved": global_best < 56,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if global_best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
