#!/usr/bin/env python3
"""Random sparse rank-23 (U,V) + solved W; multi-seed CSE cost (new basin).

Unlike UV-affine (Sun + 1–3 edits), samples fresh ternary factors.

  python3 -u tools/slp_random_rank23.py --trials 2500 --seed 44044
"""

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

from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary, write_out  # noqa: E402


def random_sparse_rows(rng, rank, nnz_range=(2, 5)):
    rows = []
    for _ in range(rank):
        k = rng.randint(nnz_range[0], nnz_range[1])
        idx = rng.sample(range(9), k)
        row = [0] * 9
        for i in idx:
            row[i] = rng.choice([-1, 1])
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=44044)
    ap.add_argument("--cse-seeds", type=int, default=8)
    ap.add_argument("--log", type=Path, default=Path("logs/random-rank23-director.log"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-random-rank23")
    )
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    rng = random.Random(args.seed)
    best = 10**9
    best_pack = None
    hist = Counter()
    brent_n = scored = 0
    t0 = time.time()
    log(f"start trials={args.trials} seed={args.seed}")

    for t in range(args.trials):
        u = random_sparse_rows(rng, 23)
        v = random_sparse_rows(rng, 23)
        W, nfree = solve_w(u, v)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None:
            continue
        if not brent_ok(u, v, w):
            continue
        brent_n += 1
        tot, sides = score_uvw(u, v, w, args.cse_seeds, args.seed + t * 31)
        if sides is None:
            continue
        scored += 1
        hist[tot] += 1
        if tot < best:
            best = tot
            best_pack = (u, v, w, sides)
            log(f"IMPROVED t={t} total={tot} brent_ok={brent_n}")
            if tot < 56:
                u, v, w, sides = best_pack
                write_out(
                    args.out,
                    u,
                    v,
                    w,
                    sides,
                    {"note": f"random rank23 t={t}", "improved": True},
                )
                break
        if (t + 1) % 500 == 0:
            log(
                f"status t={t+1} brent={brent_n} scored={scored} best={best} "
                f"elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    le56 = sum(v for k, v in hist.items() if k <= 56)
    summary = {
        "best_total": best if best < 10**9 else None,
        "improved": best < 56,
        "trials": args.trials,
        "brent_ok": brent_n,
        "scored": scored,
        "le56": le56,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
