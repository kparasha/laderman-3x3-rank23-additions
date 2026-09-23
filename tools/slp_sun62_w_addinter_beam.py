#!/usr/bin/env python3
"""W-only add_inter/drop_inter beam from Sun CSE plateau @62 (not SIDES0@56).

Prior w-addinter beam at Sun W=30 had 0 neighbors; CSE certificate W=31 may
admit inter moves that connect toward literature 56 total.

  python3 -u tools/slp_sun62_w_addinter_beam.py --max-states 25000 --max-depth 8
"""

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
from slp_w_mutate import (  # noqa: E402
    brent_ok,
    cost,
    expand,
    matches_gold,
    sun_uvw_hill,
    write_best,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--sides",
        type=Path,
        default=Path("submissions/director-agentic-sun-cse-hill/sides.json"),
    )
    ap.add_argument("--max-states", type=int, default=25_000)
    ap.add_argument("--max-depth", type=int, default=8)
    ap.add_argument("--max-w", type=int, default=40)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun62-addinter"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun62-addinter-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    u_side = deepcopy(sides["U"])
    v_side = deepcopy(sides["V"])
    gold_w, _ = expand(sides["W"])
    start = deepcopy(sides["W"])
    base_uv = cost(u_side) + cost(v_side)
    start_total = base_uv + cost(start)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    n0 = len(list(neighbors(start, gold_w)))
    log(
        f"start total={start_total} W={cost(start)} W_neighbors={n0} "
        f"max_states={args.max_states} depth={args.max_depth}"
    )

    best = deepcopy(start)
    best_w = cost(best)
    best_total = base_uv + best_w
    visited = {side_key(start)}
    heap = [(best_w, 0, 0, start)]
    tie = 1
    expanded = 0
    t0 = time.time()

    while heap and expanded < args.max_states:
        wc, depth, _, wside = heapq.heappop(heap)
        expanded += 1
        if wc < best_w:
            best_w = wc
            best = deepcopy(wside)
            best_total = base_uv + best_w
            log(
                f"IMPROVED expand={expanded} depth={depth} W={best_w} total={best_total}"
            )
            write_best(
                args.out,
                best,
                u_side,
                v_side,
                {"note": f"addinter d={depth}", "improved": best_total < 56},
            )
            if best_total < 56:
                break
        if depth >= args.max_depth:
            continue
        for cand in neighbors(wside, gold_w):
            cc = cost(cand)
            if cc > args.max_w:
                continue
            k = side_key(cand)
            if k in visited:
                continue
            visited.add(k)
            tie += 1
            heapq.heappush(heap, (cc, depth + 1, tie, cand))

    u, v, w = sun_uvw_hill(u_side, v_side, best)
    summary = {
        "start_total": start_total,
        "best_total": best_total,
        "best_W": best_w,
        "improved": best_total < 56,
        "start_W_neighbors": n0,
        "expanded": expanded,
        "visited": len(visited),
        "brent_ok": brent_ok(u, v, w),
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
