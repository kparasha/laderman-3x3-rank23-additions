#!/usr/bin/env python3
"""Random subset of terms take full triple from donor; rest from base (Sun)."""

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
    ap.add_argument("--samples", type=int, default=450)
    ap.add_argument("--k-min", type=int, default=5)
    ap.add_argument("--k-max", type=int, default=18)
    ap.add_argument("--seed", type=int, default=1230001)
    ap.add_argument("--cse-seeds", type=int, default=4)
    ap.add_argument("--base", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--donor", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-partition-graft-123"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.base.read_text(encoding="utf-8"))
    donor = json.loads(args.donor.read_text(encoding="utf-8"))
    rank = len(base["u"])
    rng = random.Random(args.seed)
    t0 = time.time()
    hits = 0
    best_cse = 10**9
    hit_ks = []
    for j in range(args.samples):
        k = rng.randint(args.k_min, min(args.k_max, rank - 1))
        terms = set(rng.sample(range(rank), k))
        data = {
            "u": deepcopy(base["u"]),
            "v": deepcopy(base["v"]),
            "w": deepcopy(base["w"]),
        }
        for t in terms:
            data["u"][t] = donor["u"][t][:]
            data["v"][t] = donor["v"][t][:]
            data["w"][t] = donor["w"][t][:]
        if not brent_ok(data["u"], data["v"], data["w"]):
            continue
        hits += 1
        hit_ks.append(k)
        tot, _ = score_uvw(data["u"], data["v"], data["w"], args.cse_seeds, args.seed + j)
        if tot is not None:
            best_cse = min(best_cse, tot)
    summary = {
        "samples": args.samples,
        "k_range": [args.k_min, args.k_max],
        "brent_ok": hits,
        "hit_k_min": min(hit_ks) if hit_ks else None,
        "hit_k_max": max(hit_ks) if hit_ks else None,
        "best_cse": best_cse if hits else None,
        "improved": hits > 0 and best_cse < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
