#!/usr/bin/env python3
"""Exhaust all C(23,2) term merges; Brent-ok and compact rank."""

from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import combinations
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from flipgraph_search import brent_residual, compact_rank  # noqa: E402
from rank_term_merge_probe import merge_pair  # noqa: E402
from slp_w_affine import brent_ok  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-merge-exhaust-117"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    t0 = time.time()
    best_rank = len(data["u"])
    brent_ok_n = 0
    for i, j in combinations(range(len(data["u"])), 2):
        trial = merge_pair(data, i, j)
        if brent_ok(trial["u"], trial["v"], trial["w"]):
            brent_ok_n += 1
            best_rank = min(best_rank, len(trial["u"]))
        comp = compact_rank(trial)
        if brent_residual(comp["u"], comp["v"], comp["w"]) == 0:
            best_rank = min(best_rank, len(comp["u"]))
    summary = {
        "pairs": 253,
        "brent_ok_merges": brent_ok_n,
        "best_rank": best_rank,
        "improved": best_rank < 23,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
