#!/usr/bin/env python3
"""Random rank-23 UV with denser rows (4–8 nnz); score greedy CSE when Brent-ok."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_random_rank23 import random_sparse_rows  # noqa: E402
from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary, write_out  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=850)
    ap.add_argument("--seed", type=int, default=1090001)
    ap.add_argument("--cse-seeds", type=int, default=6)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-random-rank23-dense-109")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    nnz = (4, 8)
    best = 10**9
    brent_n = scored = 0
    hist = Counter()
    t0 = time.time()
    for t in range(args.trials):
        u = random_sparse_rows(rng, 23, nnz)
        v = random_sparse_rows(rng, 23, nnz)
        W, _ = solve_w(u, v)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None or not brent_ok(u, v, w):
            continue
        brent_n += 1
        tot, sides = score_uvw(u, v, w, args.cse_seeds, args.seed + t * 31)
        if sides is None:
            continue
        scored += 1
        hist[tot] += 1
        if tot < best:
            best = tot
            if tot < 56:
                write_out(
                    args.out,
                    u,
                    v,
                    w,
                    sides,
                    {"note": "dense random rank23", "trial": t},
                )
                break
    summary = {
        "nnz_range": list(nnz),
        "trials": args.trials,
        "brent_ok": brent_n,
        "scored": scored,
        "best_total": best if best < 10**9 else None,
        "le56": sum(v for k, v in hist.items() if k <= 56),
        "improved": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
