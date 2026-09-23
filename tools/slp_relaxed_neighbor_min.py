#!/usr/bin/env python3
"""Min total cost among one-step relaxed add_inter neighbors of a sides certificate."""

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

from slp_relaxed_add_inter import add_inter_relaxed  # noqa: E402
from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import expand, matches_gold  # noqa: E402


def min_relaxed_neighbor(sides):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    start = total_cost(sides)
    best = start
    count = 0
    for name in ("U", "V", "W"):
        _, vs = expand(sides[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    cand = add_inter_relaxed(sides[name], golds[name], a, b, sign, 1)
                    if cand is None:
                        continue
                    trial = deepcopy(sides)
                    trial[name] = cand
                    if not all(matches_gold(trial[k], golds[k]) for k in ("U", "V", "W")):
                        continue
                    count += 1
                    best = min(best, total_cost(trial))
    return start, best, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-relaxed-neighbor-min"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    t0 = time.time()
    start, best, count = min_relaxed_neighbor(sides)
    summary = {
        "start_total": start,
        "min_relaxed_neighbor": best,
        "neighbor_count": count,
        "beats56": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["beats56"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
