#!/usr/bin/env python3
"""@62: relaxed add_inter shells at cost+1, then downhill strict hill each."""

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
from slp_sun62_uphill_shell import downhill_hill  # noqa: E402
from slp_w_mutate import SIDES0, expand, matches_gold, write_best  # noqa: E402


def collect_shells(start, target_cost):
    golds = {n: expand(start[n])[0] for n in ("U", "V", "W")}
    seen = {}
    for name in ("U", "V", "W"):
        _, vs = expand(start[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    cand = add_inter_relaxed(start[name], golds[name], a, b, sign, 1)
                    if cand is None:
                        continue
                    trial = deepcopy(start)
                    trial[name] = cand
                    if not all(matches_gold(trial[k], golds[k]) for k in ("U", "V", "W")):
                        continue
                    tc = total_cost(trial)
                    if tc != target_cost:
                        continue
                    k = scheme_key(trial)
                    seen.setdefault(k, trial)
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--sides", type=Path, default=Path("submissions/director-agentic-sun-cse-hill/sides.json")
    )
    ap.add_argument("--hill-rounds", type=int, default=1500)
    ap.add_argument("--max-shells", type=int, default=20)
    ap.add_argument("--seed", type=int, default=940001)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-relaxed-uphill-shell")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}
    start_t = total_cost(start)
    t0 = time.time()
    shells = collect_shells(start, start_t + 1)
    hist = {}
    for name in ("U", "V", "W"):
        _, vs = expand(start[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    cand = add_inter_relaxed(start[name], golds[name], a, b, sign, 1)
                    if cand is None:
                        continue
                    trial = deepcopy(start)
                    trial[name] = cand
                    if not all(matches_gold(trial[k], golds[k]) for k in ("U", "V", "W")):
                        continue
                    tc = total_cost(trial)
                    hist[tc] = hist.get(tc, 0) + 1

    global_best = start_t
    global_sides = start
    for i, shell in enumerate(shells[: args.max_shells]):
        best, bt = downhill_hill(shell, golds, args.hill_rounds, args.seed + i)
        if bt < global_best:
            global_best = bt
            global_sides = best

    summary = {
        "start_total": start_t,
        "relaxed_cost_hist": dict(sorted(hist.items())),
        "shells_at_plus1": len(shells),
        "shells_hilled": min(len(shells), args.max_shells),
        "best_total": global_best,
        "improved": global_best < 56,
        "beats62": global_best < start_t,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if global_best < 56:
        write_best(args.out, global_sides["W"], global_sides["U"], global_sides["V"], {"note": "relaxed uphill"})
    return 0 if global_best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
