#!/usr/bin/env python3
"""Best-first beam on scheme sides (multi-step mutate chains).

Stapleton hill: 64→63 then flat @150k. Beam explores lowering and mild uphill
steps from a strong start certificate.

  python3 -u tools/slp_scheme_sides_beam.py \\
      submissions/director-agentic-stapleton-sides-hill/sides.json \\
      --max-states 18000 --max-depth 7 --seed 320001
"""

from __future__ import annotations

import argparse
import heapq
import json
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import (  # noqa: E402
    brent_ok,
    cost,
    expand,
    matches_gold,
    mutate,
    sun_uvw_hill,
    write_best,
)


def scheme_key(sides) -> str:
    return json.dumps(
        {k: {"inter": sides[k]["inter"], "final": sides[k]["final"]} for k in ("U", "V", "W")},
        sort_keys=True,
        separators=(",", ":"),
    )


def random_neighbors(sides, golds, rng, tries_per_side=40):
    seen = set()
    cur_t = total_cost(sides)
    for name in ("U", "V", "W"):
        for _ in range(tries_per_side):
            cand, _ = mutate(sides[name], golds[name], rng)
            if cand is None or not matches_gold(cand, golds[name]):
                continue
            trial = deepcopy(sides)
            trial[name] = cand
            tt = total_cost(trial)
            if tt > cur_t + 2:
                continue
            k = scheme_key(trial)
            if k in seen:
                continue
            seen.add(k)
            yield tt, trial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sides_path", type=Path)
    ap.add_argument("--max-states", type=int, default=18_000)
    ap.add_argument("--max-depth", type=int, default=7)
    ap.add_argument("--seed", type=int, default=320001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-stapleton-sides-beam"))
    ap.add_argument("--log", type=Path, default=Path("logs/stapleton-sides-beam-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides_path.read_text(encoding="utf-8"))
    golds = {n: expand(start[n])[0] for n in ("U", "V", "W")}

    best = deepcopy(start)
    best_t = total_cost(best)
    visited = {scheme_key(start)}

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start total={best_t} max_states={args.max_states} depth={args.max_depth} seed={args.seed}")
    write_best(
        args.out,
        best["W"],
        best["U"],
        best["V"],
        {"note": "beam start", "improved": best_t < 56, "baseline_total": best_t},
    )

    heap = [(best_t, 0, 0, start)]
    tie = 1
    expanded = 0
    rng = random.Random(args.seed)
    t0 = time.time()

    while heap and expanded < args.max_states:
        c, depth, _, sides = heapq.heappop(heap)
        expanded += 1
        if c < best_t:
            best_t = c
            best = deepcopy(sides)
            log(
                f"IMPROVED expand={expanded} depth={depth} total={best_t} "
                f"U={cost(best['U'])} V={cost(best['V'])} W={cost(best['W'])}"
            )
            u, v, w = sun_uvw_hill(best["U"], best["V"], best["W"])
            if not brent_ok(u, v, w):
                log("ERROR brent broke")
                return 2
            write_best(
                args.out,
                best["W"],
                best["U"],
                best["V"],
                {"note": f"beam d={depth}", "improved": best_t < 56, "total": best_t},
            )
            if best_t < 56:
                break
        if depth >= args.max_depth:
            continue
        for tt, trial in random_neighbors(sides, golds, rng):
            k = scheme_key(trial)
            if k in visited:
                continue
            visited.add(k)
            tie += 1
            heapq.heappush(heap, (tt, depth + 1, tie, trial))

    elapsed = time.time() - t0
    summary = {
        "start_total": total_cost(start),
        "best_total": best_t,
        "improved": best_t < 56,
        "expanded": expanded,
        "visited": len(visited),
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_t < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
