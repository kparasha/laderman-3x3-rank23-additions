#!/usr/bin/env python3
"""SA on scheme sides (Laderman etc.): uphill moves escape cost plateaus.

Greedy hill on Laderman sides: 120k rounds, 13833 accepts, 0 improvements @65.

  python3 -u tools/slp_scheme_sides_sa.py \\
      submissions/director-add-laderman-cse/sides.json \\
      submissions/director-add-laderman-cse/solution.json \\
      --steps 90000 --seed 290002
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import (  # noqa: E402
    cost,
    expand,
    matches_gold,
    mutate,
    write_best,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sides_path", type=Path)
    ap.add_argument("solution_path", type=Path)
    ap.add_argument("--steps", type=int, default=90_000)
    ap.add_argument("--seed", type=int, default=290002)
    ap.add_argument("--t0", type=float, default=2.5)
    ap.add_argument("--tmin", type=float, default=0.04)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-laderman-sides-sa"))
    ap.add_argument("--log", type=Path, default=Path("logs/laderman-sides-sa-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    sides0 = json.loads(args.sides_path.read_text(encoding="utf-8"))
    json.loads(args.solution_path.read_text(encoding="utf-8"))

    golds = {n: expand(sides0[n])[0] for n in ("U", "V", "W")}
    cur = deepcopy(sides0)
    cur_t = total_cost(cur)
    best = deepcopy(cur)
    best_t = cur_t
    start_t = cur_t

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start total={start_t} steps={args.steps} seed={args.seed} T0={args.t0}"
    )
    write_best(
        args.out,
        best["W"],
        best["U"],
        best["V"],
        {"note": "SA start", "improved": best_t < 56, "baseline_total": start_t},
    )

    rng = random.Random(args.seed)
    accepted = uphill = improved_n = proposals = 0
    t0 = time.time()

    for step in range(1, args.steps + 1):
        frac = step / args.steps
        T = args.t0 * (args.tmin / args.t0) ** frac
        which = rng.choice(["U", "V", "W"])
        cand, op = mutate(cur[which], golds[which], rng)
        proposals += 1
        if cand is None or not matches_gold(cand, golds[which]):
            continue
        trial = deepcopy(cur)
        trial[which] = cand
        tt = total_cost(trial)
        delta = tt - cur_t
        if delta < 0 or (T > 1e-9 and rng.random() < math.exp(-delta / T)):
            accepted += 1
            if delta > 0:
                uphill += 1
            cur, cur_t = trial, tt
            if tt < best_t:
                improved_n += 1
                log(
                    f"IMPROVED step={step} {which} {op} {best_t}->{tt} "
                    f"U={cost(cur['U'])} V={cost(cur['V'])} W={cost(cur['W'])} T={T:.3f}"
                )
                best, best_t = deepcopy(cur), tt
                cert = write_best(
                    args.out,
                    best["W"],
                    best["U"],
                    best["V"],
                    {
                        "note": f"SA step={step}",
                        "improved": best_t < 56,
                        "step": step,
                    },
                )
                if not cert["brent_ok"]:
                    log("ERROR brent broke")
                    return 2
                if best_t < 56:
                    break

        if step % 22_500 == 0:
            log(
                f"status step={step} best={best_t} cur={cur_t} T={T:.3f} "
                f"acc={accepted}/{proposals} uphill={uphill} imp={improved_n} "
                f"elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    summary = {
        "start_total": start_t,
        "best_total": best_t,
        "improved": best_t < 56,
        "improvements": improved_n,
        "uphill_accepts": uphill,
        "accepted": accepted,
        "steps": args.steps,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_t < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
