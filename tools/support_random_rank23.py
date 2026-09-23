#!/usr/bin/env python3
"""Random sparse rank-23 (U,V)+solved W: track min support among Brent-ok hits."""

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

from slp_random_rank23 import random_sparse_rows  # noqa: E402
from slp_w_affine import brent_ok, solve_w, to_int_ternary  # noqa: E402
from support_overnight import exhaustive_zero, mats, support, write_out  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=840001)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-random-rank23-support")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    t0 = time.time()
    brent_n = 0
    best_raw = 10**9
    best_lift = 10**9
    best_pack = None

    for _ in range(args.trials):
        u = random_sparse_rows(rng, 23)
        v = random_sparse_rows(rng, 23)
        W, _ = solve_w(u, v)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None or not brent_ok(u, v, w):
            continue
        brent_n += 1
        data = {"u": u, "v": v, "w": w}
        raw = support(*mats(data))
        lifted, _ = exhaustive_zero(deepcopy(data))
        lift = support(*mats(lifted))
        if lift < best_lift or (lift == best_lift and raw < best_raw):
            best_raw = raw
            best_lift = lift
            best_pack = lifted

    summary = {
        "trials": args.trials,
        "brent_ok": brent_n,
        "best_raw_support": best_raw if best_pack else None,
        "best_lift_support": best_lift if best_pack else None,
        "improved": best_lift < 152 if best_pack else False,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_pack and best_lift < 152:
        write_out(args.out, best_pack, {"note": "random rank23 support"})
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
