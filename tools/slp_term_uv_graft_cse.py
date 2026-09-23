#!/usr/bin/env python3
"""For each term t: swap Sun/Stap U,V row at t, solve W, score greedy CSE."""

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

from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary, write_out  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cse-seeds", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1100001)
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--donor", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-term-uv-graft-cse")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sun = json.loads(args.sun.read_text(encoding="utf-8"))
    stap = json.loads(args.donor.read_text(encoding="utf-8"))
    rank = len(sun["u"])
    t0 = time.time()
    best = 10**9
    brent_n = 0
    best_t = None
    rows = []
    for t in range(rank):
        u = deepcopy(sun["u"])
        v = deepcopy(sun["v"])
        u[t] = stap["u"][t][:]
        v[t] = stap["v"][t][:]
        W, _ = solve_w(u, v)
        if W is None:
            rows.append({"t": t, "brent": False, "reason": "solve_fail"})
            continue
        w = to_int_ternary(W)
        if w is None or not brent_ok(u, v, w):
            rows.append({"t": t, "brent": False, "reason": "brent_fail"})
            continue
        brent_n += 1
        tot, sides = score_uvw(u, v, w, args.cse_seeds, args.seed + t)
        rows.append({"t": t, "brent": True, "cse_total": tot})
        if tot is not None and tot < best:
            best = tot
            best_t = t
            if tot < 56:
                write_out(
                    args.out,
                    u,
                    v,
                    w,
                    sides,
                    {"note": "term uv graft", "term": t},
                )
                break
    summary = {
        "trials": rank,
        "brent_ok": brent_n,
        "best_total": best if best < 10**9 else None,
        "best_term": best_t,
        "improved": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8"
    )
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
