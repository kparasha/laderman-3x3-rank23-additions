#!/usr/bin/env python3
"""BFS on Sun gold-preserving side mutates: connect CSE@62 to SIDES0@56?

  python3 -u tools/slp_sun_gold_bfs.py --start submissions/director-agentic-sun-cse-hill/sides.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import deque
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import (  # noqa: E402
    SIDES0,
    cost,
    expand,
    matches_gold,
    mutate,
    write_best,
)


def scheme_key(sides) -> str:
    return json.dumps(
        {k: {"inter": sides[k]["inter"], "final": sides[k]["final"]} for k in ("U", "V", "W")},
        sort_keys=True,
        separators=(",", ":"),
    )


def lit_key():
    return scheme_key({"U": SIDES0["U"], "V": SIDES0["V"], "W": SIDES0["W"]})


def neighbors(sides, golds, rng, tries=36):
    seen = set()
    for name in ("U", "V", "W"):
        for _ in range(tries):
            cand, _ = mutate(sides[name], golds[name], rng)
            if cand is None or not matches_gold(cand, golds[name]):
                continue
            trial = deepcopy(sides)
            trial[name] = cand
            k = scheme_key(trial)
            if k not in seen:
                seen.add(k)
                yield trial, total_cost(trial)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=Path, required=True)
    ap.add_argument("--max-states", type=int, default=14_000)
    ap.add_argument("--max-depth", type=int, default=10)
    ap.add_argument("--seed", type=int, default=380001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun-gold-bfs"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun-gold-bfs-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.start.read_text(encoding="utf-8"))
    golds = {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}
    target_k = lit_key()
    start_t = total_cost(start)
    lit_t = 56

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start total={start_t} target={lit_t} max_states={args.max_states} "
        f"depth={args.max_depth} seed={args.seed}"
    )

    rng = random.Random(args.seed)
    visited = {scheme_key(start): 0}
    q = deque([(start, 0)])
    best_t = start_t
    best_s = start
    hit_lit = False
    expanded = 0
    t0 = time.time()
    cost_hist = {}

    while q and expanded < args.max_states:
        sides, depth = q.popleft()
        expanded += 1
        tt = total_cost(sides)
        cost_hist[tt] = cost_hist.get(tt, 0) + 1
        if tt < best_t:
            best_t = tt
            best_s = deepcopy(sides)
            log(f"best={best_t} depth={depth} expanded={expanded}")
        k = scheme_key(sides)
        if k == target_k or tt <= lit_t:
            hit_lit = True
            best_s, best_t = deepcopy(sides), tt
            log(f"HIT literature schedule total={tt} depth={depth}")
            break
        if depth >= args.max_depth:
            continue
        for trial, t2 in neighbors(sides, golds, rng):
            nk = scheme_key(trial)
            if nk in visited:
                continue
            visited[nk] = depth + 1
            q.append((trial, depth + 1))

    write_best(
        args.out,
        best_s["W"],
        best_s["U"],
        best_s["V"],
        {"note": "BFS best", "improved": best_t < 56, "hit_SIDES0": hit_lit},
    )
    summary = {
        "start_total": start_t,
        "best_total": best_t,
        "hit_SIDES0": hit_lit,
        "improved": best_t < 56,
        "expanded": expanded,
        "visited": len(visited),
        "cost_hist": {str(k): v for k, v in sorted(cost_hist.items())},
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_t < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
