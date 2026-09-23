#!/usr/bin/env python3
"""Beam BFS on relaxed add_inter only (depth≤3, cap states) from Sun @62."""

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
from slp_sun_gold_bfs import scheme_key  # noqa: E402
from slp_w_mutate import expand, matches_gold, write_best  # noqa: E402


def neighbors(sides):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    out = []
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
                    if all(matches_gold(trial[k], golds[k]) for k in ("U", "V", "W")):
                        out.append(trial)
    return out


def bfs(start, max_depth, max_states):
    seen = {scheme_key(start): start}
    frontier = [start]
    best_c = total_cost(start)
    best = start
    depth = 0
    while frontier and depth < max_depth and len(seen) < max_states:
        nxt = []
        for sides in frontier:
            for trial in neighbors(sides):
                k = scheme_key(trial)
                if k in seen:
                    continue
                seen[k] = trial
                c = total_cost(trial)
                if c < best_c:
                    best_c = c
                    best = trial
                nxt.append(trial)
                if len(seen) >= max_states:
                    break
            if len(seen) >= max_states:
                break
        frontier = nxt
        depth += 1
    return len(seen), best_c, best, depth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--max-states", type=int, default=800)
    ap.add_argument(
        "--sides", type=Path, default=Path("submissions/director-agentic-sun-cse-hill/sides.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-relaxed-beam-smoke")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides.read_text(encoding="utf-8"))
    t0 = time.time()
    n, best_c, best, depth_reached = bfs(start, args.depth, args.max_states)
    summary = {
        "start_cost": total_cost(start),
        "visited": n,
        "depth_reached": depth_reached,
        "best_cost": best_c,
        "improved": best_c < total_cost(start),
        "beats56": best_c < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_c < 56:
        write_best(args.out, best["W"], best["U"], best["V"], {"note": "relaxed beam"})
    return 0 if best_c < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
