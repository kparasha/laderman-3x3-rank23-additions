#!/usr/bin/env python3
"""Zero U[t][i], V[t][i], W[t][i] together when Brent-ok; then exhaustive_zero."""

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

from support_overnight import brent_ok, exhaustive_zero, mats, support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-coord-triple-zero")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    u, v, w = mats(base)
    rank = len(u)
    t0 = time.time()
    start = support(u, v, w)
    best = start
    hits = 0
    for t in range(rank):
        for i in range(9):
            if u[t][i] == 0 and v[t][i] == 0 and w[t][i] == 0:
                continue
            trial = deepcopy(base)
            tu, tv, tw = mats(trial)
            tu[t][i] = tv[t][i] = tw[t][i] = 0
            trial = {"u": tu, "v": tv, "w": tw}
            if not brent_ok(*mats(trial)):
                continue
            hits += 1
            trial, _ = exhaustive_zero(trial)
            s = support(*mats(trial))
            if s < best:
                best = s

    summary = {
        "start_support": start,
        "best_support": best,
        "coord_hits": hits,
        "tried_cells": rank * 9,
        "improved": best < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
