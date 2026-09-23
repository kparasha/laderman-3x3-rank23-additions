#!/usr/bin/env python3
"""Depth-2 BFS: level1=relaxed only, level2=mutate sample (smoke-scale)."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_gold_bridge_probe import mutate_sample, relaxed_neighbors  # noqa: E402
from slp_sun_gold_bfs import scheme_key  # noqa: E402
from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import SIDES0, expand  # noqa: E402


def golds():
    return {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}


def bfs_lite(start, target_key, mut_tries, max_level1, seed):
    rng = random.Random(seed)
    start_k = scheme_key(start)
    visited = {start_k}
    level1 = []
    for trial in relaxed_neighbors(start):
        k = scheme_key(trial)
        if k in visited:
            continue
        visited.add(k)
        if k == target_key:
            return True, 1, len(visited)
        level1.append(trial)
        if len(level1) >= max_level1:
            break
    for trial in level1:
        for t2 in mutate_sample(trial, golds(), rng, mut_tries):
            k = scheme_key(t2)
            if k in visited:
                continue
            visited.add(k)
            if k == target_key:
                return True, 2, len(visited)
    return False, None, len(visited)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-level1", type=int, default=60)
    ap.add_argument("--mut-tries", type=int, default=150)
    ap.add_argument("--seed", type=int, default=780001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-gold-bfs-depth2"))
    ap.add_argument("--log", type=Path, default=Path("logs/gold-bfs-depth2-cycle78.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    sides56 = {"U": SIDES0["U"], "V": SIDES0["V"], "W": SIDES0["W"]}
    sides62 = json.loads(
        Path("submissions/director-agentic-sun-cse-hill/sides.json").read_text(encoding="utf-8")
    )
    k56, k62 = scheme_key(sides56), scheme_key(sides62)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    h62, d62, v62 = bfs_lite(sides62, k56, args.mut_tries, args.max_level1, args.seed)
    h56, d56, v56 = bfs_lite(sides56, k62, args.mut_tries, args.max_level1, args.seed + 1)
    summary = {
        "cost56": total_cost(sides56),
        "cost62": total_cost(sides62),
        "62_to_56": {"hit": h62, "depth": d62, "visited": v62},
        "56_to_62": {"hit": h56, "depth": d56, "visited": v56},
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if h62 or h56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
