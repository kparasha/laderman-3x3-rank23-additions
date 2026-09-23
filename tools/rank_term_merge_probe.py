#!/usr/bin/env python3
"""Merge two rank-1 terms (U+=U', zero one row) and compact; check Brent rank."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from flipgraph_search import brent_residual, compact_rank  # noqa: E402
from slp_w_affine import brent_ok  # noqa: E402


def merge_pair(data, i, j):
    u = [r[:] for r in data["u"]]
    v = [r[:] for r in data["v"]]
    w = [r[:] for r in data["w"]]
    u[i] = [a + b for a, b in zip(u[i], u[j])]
    v[i] = [a + b for a, b in zip(v[i], v[j])]
    w[i] = [a + b for a, b in zip(w[i], w[j])]
    del u[j]
    del v[j]
    del w[j]
    return {"u": u, "v": v, "w": w}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=400)
    ap.add_argument("--seed", type=int, default=880002)
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-term-merge-rank"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    pairs = list(combinations(range(len(data["u"])), 2))
    rng = random.Random(args.seed)
    rng.shuffle(pairs)
    pairs = pairs[: args.samples]
    t0 = time.time()
    best_rank = len(data["u"])
    hits = []
    for i, j in pairs:
        trial = merge_pair(data, i, j)
        if brent_ok(trial["u"], trial["v"], trial["w"]):
            r = len(trial["u"])
            hits.append((r, i, j))
            best_rank = min(best_rank, r)
        comp = compact_rank(trial)
        if brent_residual(comp["u"], comp["v"], comp["w"]) == 0:
            r = len(comp["u"])
            if r < best_rank:
                best_rank = r

    summary = {
        "samples": len(pairs),
        "brent_ok_merges": len(hits),
        "best_rank": best_rank,
        "improved": best_rank < 23,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
