#!/usr/bin/env python3
"""Wide multi-seed greedy CSE fan on fixed UVW — tests seed sensitivity of certified total."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import brent_ok, score_uvw, write_out  # noqa: E402
from slp_w_mutate import SIDES0, cost  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=384)
    ap.add_argument("--base-seed", type=int, default=820001)
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-cse-seed-fan")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    u, v, w = base["u"], base["v"], base["w"]
    assert brent_ok(u, v, w)

    sides56 = cost(SIDES0["U"]) + cost(SIDES0["V"]) + cost(SIDES0["W"])
    t0 = time.time()
    best = 10**9
    best_pack = None
    hist = {}

    for s in range(args.seeds):
        tot, sides = score_uvw(u, v, w, 1, args.base_seed + s * 7919)
        if tot is None:
            continue
        hist[tot] = hist.get(tot, 0) + 1
        if tot < best:
            best = tot
            best_pack = (tot, sides, s)

    summary = {
        "src": str(args.src),
        "seeds": args.seeds,
        "sides0_total": sides56,
        "best_total": best,
        "improved": best < 56,
        "hist_top5": sorted(hist.items(), key=lambda x: x[0])[:5],
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_pack and best < 56:
        tot, sides, s = best_pack
        write_out(args.out, u, v, w, sides, {"note": "cse seed fan", "win_seed": s})
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
