#!/usr/bin/env python3
"""W-only addinter beam from arbitrary sides.json (U,V,W); U/V frozen."""

from __future__ import annotations

import argparse
import heapq
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_addinter_beam import neighbors  # noqa: E402
from slp_w_beam import side_key  # noqa: E402
from slp_w_mutate import brent_ok, cost, expand, sun_uvw_hill, write_best  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, required=True)
    ap.add_argument("--max-states", type=int, default=1200)
    ap.add_argument("--max-depth", type=int, default=5)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-w-beam-custom"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    u_side, v_side, start = sides["U"], sides["V"], deepcopy(sides["W"])
    gold_w, _ = expand(start)
    base_uv = cost(u_side) + cost(v_side)
    best = deepcopy(start)
    best_c = cost(best)
    visited = {side_key(start)}
    n0 = len(list(neighbors(start, gold_w)))
    heap = [(best_c, 0, 0, start)]
    tie = expanded = 0
    t0 = time.time()
    while heap and expanded < args.max_states:
        c, depth, _, side = heapq.heappop(heap)
        expanded += 1
        if c < best_c:
            best_c = c
            best = deepcopy(side)
            if best_c <= 29:
                break
        if depth >= args.max_depth:
            continue
        for cand in neighbors(side, gold_w):
            cc = cost(cand)
            k = side_key(cand)
            if k in visited:
                continue
            visited.add(k)
            tie += 1
            heapq.heappush(heap, (cc, depth + 1, tie, cand))

    total = base_uv + best_c
    summary = {
        "src": str(args.sides),
        "start_W": cost(start),
        "W": best_c,
        "total": total,
        "start_neighbors": n0,
        "expanded": expanded,
        "visited": len(visited),
        "improved": total < 56,
        "elapsed_s": time.time() - t0,
        "brent_ok": brent_ok(*sun_uvw_hill(u_side, v_side, best)),
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if total < 56:
        write_best(args.out, best, u_side, v_side, {"note": "w beam custom"})
    return 0 if total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
