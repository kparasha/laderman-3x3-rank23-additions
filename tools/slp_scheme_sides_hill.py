#!/usr/bin/env python3
"""Gold-preserving hill climb on scheme sides (U/V/W mutate), not matrix CSE.

Sun SIDES graph is isolated at 56. Laderman greedy-CSE sides (≈65) have UV
neighbors; this walks total cost down toward <56 on the same Brent-ok tensor.

  python3 -u tools/slp_scheme_sides_hill.py \\
      submissions/director-add-laderman-cse/sides.json \\
      submissions/director-add-laderman-cse/solution.json \\
      --rounds 120000 --seed 290001
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

from slp_w_mutate import (  # noqa: E402
    brent_ok,
    cost,
    expand,
    matches_gold,
    mutate,
    sun_uvw_hill,
    write_best,
)


def total_cost(sides):
    return cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sides_path", type=Path)
    ap.add_argument("solution_path", type=Path)
    ap.add_argument("--rounds", type=int, default=120_000)
    ap.add_argument("--seed", type=int, default=290001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-laderman-sides-hill"))
    ap.add_argument("--log", type=Path, default=Path("logs/laderman-sides-hill-director.log"))
    ap.add_argument("--diversify-p", type=float, default=0.03)
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    sides0 = json.loads(args.sides_path.read_text(encoding="utf-8"))
    sol0 = json.loads(args.solution_path.read_text(encoding="utf-8"))
    assert brent_ok(sol0["u"], sol0["v"], sol0["w"])

    golds = {}
    for name in ("U", "V", "W"):
        g, _ = expand(sides0[name])
        golds[name] = g

    cur = deepcopy(sides0)
    cur_t = total_cost(cur)
    best = deepcopy(cur)
    best_t = cur_t

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start total={best_t} U={cost(best['U'])} V={cost(best['V'])} "
        f"W={cost(best['W'])} rounds={args.rounds} seed={args.seed}"
    )
    write_best(
        args.out,
        best["W"],
        best["U"],
        best["V"],
        {"note": "start", "improved": best_t < 56, "baseline_total": best_t},
    )

    rng = random.Random(args.seed)
    accepted = improved = 0
    t0 = time.time()

    for r in range(1, args.rounds + 1):
        which = rng.choice(["U", "V", "W"])
        side = cur[which]
        cand, op = mutate(side, golds[which], rng)
        if cand is None or not matches_gold(cand, golds[which]):
            continue
        accepted += 1
        trial = deepcopy(cur)
        trial[which] = cand
        tt = total_cost(trial)
        if tt < cur_t or (tt == cur_t and rng.random() < args.diversify_p):
            cur, cur_t = trial, tt
            if tt < best_t:
                improved += 1
                log(
                    f"IMPROVED r={r} side={which} op={op} "
                    f"{best_t}->{tt} U={cost(cur['U'])} V={cost(cur['V'])} W={cost(cur['W'])}"
                )
                best, best_t = deepcopy(cur), tt
                cert = write_best(
                    args.out,
                    best["W"],
                    best["U"],
                    best["V"],
                    {
                        "note": f"r={r} {which} {op}",
                        "improved": best_t < 56,
                        "baseline_total": total_cost(sides0),
                        "round": r,
                    },
                )
                if not cert["brent_ok"]:
                    log("ERROR brent broke")
                    return 2
                if best_t < 56:
                    break

        if r % 30_000 == 0:
            log(
                f"status r={r} best={best_t} cur={cur_t} acc={accepted} "
                f"imp={improved} elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    summary = {
        "start_total": total_cost(sides0),
        "best_total": best_t,
        "improved": best_t < 56,
        "improvements": improved,
        "accepted": accepted,
        "rounds": args.rounds,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_t < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
