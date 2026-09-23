#!/usr/bin/env python3
"""Histogram total_cost under exhaustive relaxed add_inter from a sides cert."""

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-relax-cost-hist56"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(start[n])[0] for n in ("U", "V", "W")}
    start_c = total_cost(start)
    hist = {}
    t0 = time.time()
    for name in ("U", "V", "W"):
        _, vs = expand(start[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    cand = add_inter_relaxed(start[name], golds[name], a, b, sign, 1)
                    if cand is None:
                        continue
                    trial = deepcopy(start)
                    trial[name] = cand
                    if not all(matches_gold(trial[k], golds[k]) for k in ("U", "V", "W")):
                        continue
                    c = total_cost(trial)
                    hist[c] = hist.get(c, 0) + 1

    summary = {
        "start_cost": start_c,
        "hist": dict(sorted(hist.items())),
        "min_neighbor": min(hist.keys()) if hist else start_c,
        "below_start": sum(v for k, v in hist.items() if k < start_c),
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary.get("min_neighbor", start_c) < start_c else 1


if __name__ == "__main__":
    raise SystemExit(main())
