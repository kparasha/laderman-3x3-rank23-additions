#!/usr/bin/env python3
"""Sun UVW: scan rebuild_sides seeds, then sides-hill toward <56.

All rank-23 schemes here share the same Brent tensor; Stapleton sides hill
descended 64→63. Sun literature SIDES=56; greedy rebuild + mutate may bridge.

  python3 -u tools/slp_sun_rebuild_hill.py --scan-seeds 48 --rounds 130000 --seed 350001
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_addition_search import rebuild_sides_from_uvw, total_cost  # noqa: E402
from slp_scheme_sides_hill import total_cost as tc  # noqa: E402
from slp_w_mutate import SIDES0, cost, expand, matches_gold, mutate, write_best  # noqa: E402


def hill_from(sides0, rounds, seed, log):
    golds = {n: expand(sides0[n])[0] for n in ("U", "V", "W")}
    cur = deepcopy(sides0)
    cur_t = tc(cur)
    best = deepcopy(cur)
    best_t = cur_t
    import random

    rng = random.Random(seed)
    improved = accepted = 0
    for r in range(1, rounds + 1):
        which = rng.choice(["U", "V", "W"])
        cand, op = mutate(cur[which], golds[which], rng)
        if cand is None or not matches_gold(cand, golds[which]):
            continue
        accepted += 1
        trial = deepcopy(cur)
        trial[which] = cand
        tt = tc(trial)
        if tt < cur_t or (tt == cur_t and rng.random() < 0.03):
            cur, cur_t = trial, tt
            if tt < best_t:
                improved += 1
                log(
                    f"IMPROVED r={r} {which} {op} {best_t}->{tt} "
                    f"U={cost(cur['U'])} V={cost(cur['V'])} W={cost(cur['W'])}"
                )
                best, best_t = deepcopy(cur), tt
                if best_t < 56:
                    return best, best_t, improved, accepted
    return best, best_t, improved, accepted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--scan-seeds", type=int, default=48)
    ap.add_argument("--rounds", type=int, default=130_000)
    ap.add_argument("--seed", type=int, default=350001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun-rebuild-hill"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun-rebuild-hill-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.sun.read_text(encoding="utf-8"))
    u, v, w = data["u"], data["v"], data["w"]
    lit = total_cost(SIDES0)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    best_scan = 10**9
    best_sides = None
    best_seed = 0
    for s in range(args.scan_seeds):
        sides = rebuild_sides_from_uvw(u, v, w, seed=s)
        if sides is None:
            continue
        c = total_cost(sides)
        if c < best_scan:
            best_scan, best_sides, best_seed = c, sides, s
    log(f"scan seeds={args.scan_seeds} best_rebuild={best_scan} seed={best_seed} literature={lit}")

    starts = [("SIDES0", SIDES0)]
    if best_sides and best_scan < 10**9:
        starts.append((f"rebuild_{best_seed}", best_sides))

    global_best = lit
    global_sides = SIDES0
    label = "SIDES0"
    for name, start in starts:
        log(f"hill from {name} total={tc(start)} rounds={args.rounds}")
        b, bt, imp, acc = hill_from(start, args.rounds, args.seed + hash(name) % 10000, log)
        log(f"done {name} best={bt} imp={imp} acc={acc}")
        if bt < global_best:
            global_best, global_sides, label = bt, b, name
        if global_best < 56:
            break

    write_best(
        args.out,
        global_sides["W"],
        global_sides["U"],
        global_sides["V"],
        {"note": f"best from {label}", "improved": global_best < 56, "total": global_best},
    )
    summary = {
        "literature": lit,
        "best_rebuild_scan": best_scan,
        "best_total": global_best,
        "improved": global_best < 56,
        "best_from": label,
        "elapsed_s": time.time() - t0,
    }
    log(f"summary {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if global_best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
