#!/usr/bin/env python3
"""Simulated-annealing escape on Sun W SLP (U/V frozen at 13+13).

Greedy W mutate never accepts worse cost, so it plateaus at W=30 (total 56).
This walk allows uphill W moves with cooling so schedules can traverse
equal-gold rearrangements that require a temporary extra intermediate.

  python3 -u tools/slp_w_sa_escape.py --steps 350000 --seed 8181 \\
      --log logs/w-sa-director.log --out submissions/director-agentic-w-sa
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

from slp_uv_mutate import fixpoint_pass  # noqa: E402
from slp_w_mutate import (  # noqa: E402
    SIDES0,
    brent_ok,
    cost,
    expand,
    matches_gold,
    mutate,
    sun_uvw_hill,
    write_best,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=350_000)
    ap.add_argument("--seed", type=int, default=8181)
    ap.add_argument("--t0", type=float, default=3.0)
    ap.add_argument("--tmin", type=float, default=0.03)
    ap.add_argument("--log", type=Path, default=Path("logs/w-sa-director.log"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-w-sa"))
    ap.add_argument("--status-every", type=int, default=25_000)
    ap.add_argument("--fixpoint", action="store_true", default=True)
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    u_side = deepcopy(SIDES0["U"])
    v_side = deepcopy(SIDES0["V"])
    gold_w, _ = expand(SIDES0["W"])
    rng_fp = random.Random(args.seed)
    w_side, w_c = fixpoint_pass(deepcopy(SIDES0["W"]), gold_w, rng_fp)
    base_uv = cost(u_side) + cost(v_side)

    cur = deepcopy(w_side)
    cur_c = w_c
    best = deepcopy(cur)
    best_c = cur_c

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start W={best_c} total={base_uv + best_c} fixpoint={args.fixpoint} "
        f"steps={args.steps} seed={args.seed} T0={args.t0}"
    )
    write_best(
        args.out,
        best,
        u_side,
        v_side,
        {"note": "W SA start", "improved": best_c < 30, "baseline_W": 30},
    )

    rng = random.Random(args.seed + 4242)
    accepted = uphill = improved_n = proposals = 0
    t0 = time.time()

    for step in range(1, args.steps + 1):
        frac = step / args.steps
        T = args.t0 * (args.tmin / args.t0) ** frac
        cand, op = mutate(cur, gold_w, rng)
        proposals += 1
        if cand is None or not matches_gold(cand, gold_w):
            continue
        cc = cost(cand)
        delta = cc - cur_c
        if delta < 0 or (T > 1e-9 and rng.random() < math.exp(-delta / T)):
            accepted += 1
            if delta > 0:
                uphill += 1
            cur, cur_c = cand, cc
            if cc < best_c:
                improved_n += 1
                log(
                    f"IMPROVED step={step} op={op} W {best_c}->{cc} "
                    f"total {base_uv + best_c}->{base_uv + cc} T={T:.3f}"
                )
                best, best_c = deepcopy(cur), cc
                cert = write_best(
                    args.out,
                    best,
                    u_side,
                    v_side,
                    {
                        "note": f"W SA step={step} op={op}",
                        "improved": best_c < 30,
                        "baseline_W": 30,
                        "step": step,
                    },
                )
                if not cert["brent_ok"]:
                    log("ERROR brent broke after improve")
                    return 2
                if best_c <= 29:
                    break

        if step % args.status_every == 0:
            log(
                f"status step={step} best_W={best_c} cur_W={cur_c} "
                f"total={base_uv + best_c} T={T:.3f} acc={accepted}/{proposals} "
                f"uphill={uphill} imp={improved_n} elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    total = base_uv + best_c
    summary = {
        "W": best_c,
        "total": total,
        "baseline_total": 56,
        "improved": total < 56,
        "steps": args.steps,
        "accepted": accepted,
        "uphill_accepts": uphill,
        "improvements": improved_n,
        "elapsed_s": elapsed,
        "brent_ok": brent_ok(*sun_uvw_hill(u_side, v_side, best)),
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
