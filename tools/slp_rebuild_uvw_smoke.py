#!/usr/bin/env python3
"""Multi-seed greedy side rebuild from fixed Brent-ok UVW; min certified total."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_addition_search import rebuild_sides_from_uvw, total_cost  # noqa: E402
from slp_w_affine import brent_ok  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--trials", type=int, default=80)
    ap.add_argument("--seed-base", type=int, default=1220002)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rebuild-uvw-smoke-122"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    u, v, w = data["u"], data["v"], data["w"]
    assert brent_ok(u, v, w)
    t0 = time.time()
    best = 10**9
    for t in range(args.trials):
        sides = rebuild_sides_from_uvw(u, v, w, args.seed_base + t * 9973)
        if sides is None:
            continue
        tot = total_cost(sides)
        best = min(best, tot)
    summary = {
        "src": str(args.src),
        "trials": args.trials,
        "best_total": best if best < 10**9 else None,
        "improved": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
