#!/usr/bin/env python3
"""Per-term Sun/Stapleton UV mosaic + solved W; score CSE and support."""

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

from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary  # noqa: E402
from support_overnight import exhaustive_zero, mats, support  # noqa: E402


def mosaic(sun, stap, mask):
    u, v = [], []
    for t in range(len(sun["u"])):
        src = sun if mask[t] else stap
        u.append(src["u"][t][:])
        v.append(src["v"][t][:])
    return u, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=900)
    ap.add_argument("--seed", type=int, default=950001)
    ap.add_argument("--cse-seeds", type=int, default=6)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-uv-mosaic-solve")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sun = json.loads(Path("submissions/sun56/solution.json").read_text(encoding="utf-8"))
    stap = json.loads(Path("submissions/stapleton60/solution.json").read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    brent_n = scored = 0
    best_add = 10**9
    best_sup = 10**9
    le56 = 0
    lt152 = 0

    for trial in range(args.trials):
        mask = [rng.random() < 0.5 for _ in range(23)]
        if all(mask) or not any(mask):
            mask[rng.randrange(23)] = not mask[rng.randrange(23)]
        u, v = mosaic(sun, stap, mask)
        W, _ = solve_w(u, v)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None or not brent_ok(u, v, w):
            continue
        brent_n += 1
        tot, sides = score_uvw(u, v, w, args.cse_seeds, args.seed + trial * 13)
        if sides is None:
            continue
        scored += 1
        data = {"u": u, "v": v, "w": w}
        data_z, _ = exhaustive_zero(deepcopy(data))
        sup = support(*mats(data_z))
        if tot <= 56:
            le56 += 1
        if sup < 152:
            lt152 += 1
        if tot < best_add:
            best_add = tot
        if sup < best_sup:
            best_sup = sup

    summary = {
        "trials": args.trials,
        "brent_ok": brent_n,
        "scored": scored,
        "best_additions": best_add if scored else None,
        "best_support": best_sup if brent_n else None,
        "le56": le56,
        "lt152": lt152,
        "improved_add": best_add < 56 if scored else False,
        "improved_sup": best_sup < 152 if brent_n else False,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved_add"] or summary["improved_sup"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
