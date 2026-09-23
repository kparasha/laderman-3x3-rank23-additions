#!/usr/bin/env python3
"""Random k=4 full triple grafts: Sun base + Stapleton donor on 4 terms."""

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

from slp_w_affine import brent_ok, score_uvw  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=500)
    ap.add_argument("--seed", type=int, default=1200001)
    ap.add_argument("--cse-seeds", type=int, default=6)
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--donor", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-k4-graft-smoke-120"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sun = json.loads(args.sun.read_text(encoding="utf-8"))
    stap = json.loads(args.donor.read_text(encoding="utf-8"))
    rank = len(sun["u"])
    rng = random.Random(args.seed)
    t0 = time.time()
    hits = 0
    best_cse = 10**9
    for j in range(args.samples):
        terms = rng.sample(range(rank), 4)
        data = {"u": deepcopy(sun["u"]), "v": deepcopy(sun["v"]), "w": deepcopy(sun["w"])}
        for t in terms:
            data["u"][t] = stap["u"][t][:]
            data["v"][t] = stap["v"][t][:]
            data["w"][t] = stap["w"][t][:]
        if not brent_ok(data["u"], data["v"], data["w"]):
            continue
        hits += 1
        tot, _ = score_uvw(data["u"], data["v"], data["w"], args.cse_seeds, args.seed + j)
        if tot is not None:
            best_cse = min(best_cse, tot)
    summary = {
        "k": 4,
        "samples": args.samples,
        "brent_ok": hits,
        "best_cse": best_cse if hits else None,
        "improved_adds": hits > 0 and best_cse < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved_adds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
