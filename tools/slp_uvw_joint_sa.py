#!/usr/bin/env python3
"""Joint SA on Sun U/V/W SLP schedules (gold-preserving per side).

Greedy W-only and UV-only (W frozen) plateau at 56. This walk accepts uphill
moves on total certified cost so UV can rise temporarily while W falls.

  python3 -u tools/slp_uvw_joint_sa.py --steps 200000 --seed 77 \\
      --log logs/uvw-joint-sa.log --out submissions/director-agentic-uvw-sa
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


def total_cost(u, v, w):
    return cost(u) + cost(v) + cost(w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=77)
    ap.add_argument("--t0", type=float, default=4.0)
    ap.add_argument("--tmin", type=float, default=0.02)
    ap.add_argument("--log", type=Path, default=Path("logs/uvw-joint-sa.log"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-uvw-sa"))
    ap.add_argument("--status-every", type=int, default=8000)
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    gold_u, _ = expand(SIDES0["U"])
    gold_v, _ = expand(SIDES0["V"])
    gold_w, _ = expand(SIDES0["W"])
    golds = {"U": gold_u, "V": gold_v, "W": gold_w}

    rng0 = random.Random(args.seed)
    u, cu = fixpoint_pass(deepcopy(SIDES0["U"]), gold_u, rng0)
    v, cv = fixpoint_pass(deepcopy(SIDES0["V"]), gold_v, random.Random(args.seed + 1))
    w = deepcopy(SIDES0["W"])
    cw = cost(w)

    cur = {"U": u, "V": v, "W": w}
    cur_t = total_cost(u, v, w)
    best = deepcopy(cur)
    best_t = cur_t

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start fixpoint U={cu} V={cv} W={cw} total={cur_t} "
        f"steps={args.steps} seed={args.seed} T0={args.t0}"
    )
    write_best(
        args.out,
        cur["W"],
        cur["U"],
        cur["V"],
        {"note": "joint SA start", "improved": best_t < 56, "baseline_total": 56},
    )

    rng = random.Random(args.seed + 999)
    accepted = uphill = improved_n = proposals = 0
    t0 = time.time()

    for step in range(1, args.steps + 1):
        frac = step / args.steps
        T = args.t0 * (args.tmin / args.t0) ** frac
        which = rng.choices(["U", "V", "W"], weights=[0.35, 0.35, 0.30], k=1)[0]
        side = cur[which]
        cand, op = mutate(side, golds[which], rng)
        proposals += 1
        if cand is None or not matches_gold(cand, golds[which]):
            continue
        trial = deepcopy(cur)
        trial[which] = cand
        uu, vv, ww = trial["U"], trial["V"], trial["W"]
        tot = total_cost(uu, vv, ww)
        delta = tot - cur_t
        if delta < 0 or (T > 1e-9 and rng.random() < math.exp(-delta / T)):
            accepted += 1
            if delta > 0:
                uphill += 1
            cur, cur_t = trial, tot
            if tot < best_t:
                improved_n += 1
                log(
                    f"IMPROVED step={step} side={which} op={op} "
                    f"U={cost(uu)} V={cost(vv)} W={cost(ww)} {best_t}->{tot} T={T:.3f}"
                )
                best_t = tot
                best = deepcopy(cur)
                write_best(
                    args.out,
                    best["W"],
                    best["U"],
                    best["V"],
                    {
                        "note": f"joint SA step={step} {which} {op}",
                        "improved": best_t < 56,
                        "baseline_total": 56,
                        "step": step,
                    },
                )
                u, v, w_m = sun_uvw_hill(best["U"], best["V"], best["W"])
                if not brent_ok(u, v, w_m):
                    log("ERROR brent broke after improve")
                    return 2
                if best_t < 56:
                    break

        if step % args.status_every == 0:
            log(
                f"status step={step} best={best_t} cur={cur_t} "
                f"U={cost(cur['U'])} V={cost(cur['V'])} W={cost(cur['W'])} "
                f"T={T:.3f} acc={accepted}/{proposals} uphill={uphill} "
                f"imp={improved_n} elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    u, v, w_m = sun_uvw_hill(best["U"], best["V"], best["W"])
    summary = {
        "U": cost(best["U"]),
        "V": cost(best["V"]),
        "W": cost(best["W"]),
        "total": best_t,
        "baseline": 56,
        "improved": best_t < 56,
        "steps": args.steps,
        "accepted": accepted,
        "proposals": proposals,
        "uphill_accepts": uphill,
        "improvements": improved_n,
        "elapsed_s": elapsed,
        "brent_ok": brent_ok(u, v, w_m),
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_t < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
