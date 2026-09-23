#!/usr/bin/env python3
"""Replace one full rank-1 triple (U,V,W) in Sun with Stapleton's term t."""

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
from support_overnight import exhaustive_zero, mats, support as count_support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cse-seeds", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1110001)
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--donor", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-term-triple-graft")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sun = json.loads(args.sun.read_text(encoding="utf-8"))
    stap = json.loads(args.donor.read_text(encoding="utf-8"))
    rank = len(sun["u"])
    t0 = time.time()
    best_cse = 10**9
    best_sup = 10**9
    brent_n = 0
    for t in range(rank):
        data = {
            "u": deepcopy(sun["u"]),
            "v": deepcopy(sun["v"]),
            "w": deepcopy(sun["w"]),
        }
        data["u"][t] = stap["u"][t][:]
        data["v"][t] = stap["v"][t][:]
        data["w"][t] = stap["w"][t][:]
        if not brent_ok(data["u"], data["v"], data["w"]):
            continue
        brent_n += 1
        tot, _ = score_uvw(
            data["u"], data["v"], data["w"], args.cse_seeds, args.seed + t
        )
        if tot is not None:
            best_cse = min(best_cse, tot)
        lifted, _ = exhaustive_zero(deepcopy(data))
        best_sup = min(best_sup, count_support(*mats(lifted)))
    summary = {
        "trials": rank,
        "brent_ok": brent_n,
        "best_cse": best_cse if brent_n else None,
        "best_support": best_sup if brent_n else None,
        "improved_adds": brent_n > 0 and best_cse < 56,
        "improved_support": brent_n > 0 and best_sup < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved_adds"] or summary["improved_support"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
