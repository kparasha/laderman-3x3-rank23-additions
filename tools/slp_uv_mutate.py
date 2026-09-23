#!/usr/bin/env python3
"""Gold-preserving CSE local search on Sun U and V (W frozen).

W-only mutate plateaued at 30; U/V at 13 each were never hill-climbed with the
same extract/shorten/compact moves. Brent tensor unchanged iff expand(U,V) match Sun.

  python3 -u tools/slp_uv_mutate.py --rounds 120000 --seed 42 \\
      --log logs/uv-mutate.log --out submissions/director-agentic-uv-mutate
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_mutate import (  # noqa: E402
    SIDES0,
    brent_ok,
    compact_side,
    cost,
    expand,
    matches_gold,
    mutate,
    sun_uvw_hill,
    try_extract_common_pair,
    try_shorten_one_final,
    write_best,
)


def fixpoint_pass(side, gold, rng):
    """Deterministic-ish passes: extract pairs, shorten finals, compact."""
    best = deepcopy(side)
    best_c = cost(best)
    improved = True
    while improved:
        improved = False
        for _ in range(30):
            cand = try_extract_common_pair(best, rng)
            if cand is None or not matches_gold(cand, gold):
                continue
            c = cost(cand)
            if c <= best_c:
                best, best_c = cand, c
                improved = True
        for _ in range(20):
            cand = try_shorten_one_final(best, gold, rng)
            if cand is None or not matches_gold(cand, gold):
                continue
            c = cost(cand)
            if c < best_c:
                best, best_c = cand, c
                improved = True
        compact = compact_side(best)
        if compact and matches_gold(compact, gold):
            c = cost(compact)
            if c < best_c:
                best, best_c = compact, c
                improved = True
    return best, best_c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=120_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--log", type=Path, default=Path("logs/uv-mutate.log"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-uv-mutate"))
    ap.add_argument("--status-every", type=int, default=3000)
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    w_side = deepcopy(SIDES0["W"])
    u_side = deepcopy(SIDES0["U"])
    v_side = deepcopy(SIDES0["V"])
    gold_u, _ = expand(u_side)
    gold_v, _ = expand(v_side)

    rng0 = random.Random(args.seed)
    u_side, cu = fixpoint_pass(u_side, gold_u, rng0)
    v_side, cv = fixpoint_pass(v_side, gold_v, random.Random(args.seed + 1))
    w_c = cost(w_side)
    base_total = cu + cv + w_c

    best_u, best_v = deepcopy(u_side), deepcopy(v_side)
    best_total = base_total

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"fixpoint U={cu} V={cv} W={w_c} total={base_total} "
        f"(Sun U/V/W={cost(SIDES0['U'])}/{cost(SIDES0['V'])}/{w_c}) "
        f"rounds={args.rounds} seed={args.seed}"
    )

    write_best(
        args.out,
        w_side,
        best_u,
        best_v,
        {
            "note": "after fixpoint + start UV mutate",
            "improved": best_total < 56,
            "baseline_total": 56,
            "fixpoint_U": cu,
            "fixpoint_V": cv,
        },
    )

    accepted = improved = 0
    t0 = time.time()
    sides = {"U": best_u, "V": best_v}
    golds = {"U": gold_u, "V": gold_v}

    for r in range(1, args.rounds + 1):
        rng = random.Random(args.seed * 1_000_003 + r)
        which = rng.choice(["U", "V"])
        side = sides[which]
        gold = golds[which]
        cand, op = mutate(side, gold, rng)
        if cand is None or not matches_gold(cand, gold):
            if r % args.status_every == 0:
                log(
                    f"status r={r} U={cost(sides['U'])} V={cost(sides['V'])} "
                    f"total={cost(sides['U'])+cost(sides['V'])+w_c} "
                    f"acc={accepted} imp={improved} elapsed={time.time()-t0:.1f}s"
                )
            continue
        accepted += 1
        sides[which] = cand
        tot = cost(sides["U"]) + cost(sides["V"]) + w_c
        if tot < best_total or (tot == best_total and rng.random() < 0.03):
            if tot < best_total:
                improved += 1
                log(
                    f"IMPROVED r={r} side={which} op={op} "
                    f"U={cost(sides['U'])} V={cost(sides['V'])} total {best_total}->{tot}"
                )
                best_total = tot
                best_u, best_v = deepcopy(sides["U"]), deepcopy(sides["V"])
                cert = write_best(
                    args.out,
                    w_side,
                    best_u,
                    best_v,
                    {
                        "note": f"UV mutate {which} op={op} r={r}",
                        "improved": best_total < 56,
                        "baseline_total": 56,
                        "round": r,
                    },
                )
                if not cert["brent_ok"]:
                    log("ERROR brent failed")
                    return 2
                if best_total < 56:
                    log(f"HIT total={best_total}")
                    break
            else:
                sides[which] = cand

        if r % args.status_every == 0:
            log(
                f"status r={r} U={cost(sides['U'])} V={cost(sides['V'])} "
                f"best_total={best_total} acc={accepted} imp={improved} "
                f"elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    u, v, w = sun_uvw_hill(best_u, best_v, w_side)
    summary = {
        "U": cost(best_u),
        "V": cost(best_v),
        "W": w_c,
        "total": best_total,
        "baseline": 56,
        "improved": best_total < 56,
        "accepted": accepted,
        "improved_steps": improved,
        "elapsed_s": elapsed,
        "brent_ok": brent_ok(u, v, w),
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
