#!/usr/bin/env python3
"""Keep one donor rank-1 term; fill remaining slots from base scheme."""

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

from slp_w_affine import brent_ok, score_uvw  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--donor", type=Path, required=True)
    ap.add_argument("--cse-seeds", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1210003)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-hybrid-one-donor"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.base.read_text(encoding="utf-8"))
    donor = json.loads(args.donor.read_text(encoding="utf-8"))
    rank = len(base["u"])
    t0 = time.time()
    brent_n = 0
    best_cse = 10**9
    for keep in range(rank):
        data = {
            "u": deepcopy(base["u"]),
            "v": deepcopy(base["v"]),
            "w": deepcopy(base["w"]),
        }
        data["u"][keep] = donor["u"][keep][:]
        data["v"][keep] = donor["v"][keep][:]
        data["w"][keep] = donor["w"][keep][:]
        if not brent_ok(data["u"], data["v"], data["w"]):
            continue
        brent_n += 1
        tot, _ = score_uvw(data["u"], data["v"], data["w"], args.cse_seeds, args.seed + keep)
        if tot is not None:
            best_cse = min(best_cse, tot)
    summary = {
        "base": str(args.base),
        "donor": str(args.donor),
        "brent_ok": brent_n,
        "best_cse": best_cse if brent_n else None,
        "improved": brent_n > 0 and best_cse < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
