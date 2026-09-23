#!/usr/bin/env python3
"""Greedy descent on compact rank via Brent=0 flips (batch best each step)."""

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

from flipgraph_search import brent_residual, compact_rank, flip  # noqa: E402


def compact_rank_len(data):
    comp = compact_rank(data)
    return len(comp["u"]), comp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=120)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1200002)
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-greedy-compact-120"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cur = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    start_r, _ = compact_rank_len(cur)
    cur_r = start_r
    best_r = start_r
    improvements = 0
    for _ in range(args.steps):
        best_cand = None
        best_cand_r = cur_r
        for _ in range(args.batch):
            trial = flip(cur, rng)
            if brent_residual(trial["u"], trial["v"], trial["w"]) != 0:
                continue
            r, comp = compact_rank_len(trial)
            if r < best_cand_r:
                best_cand_r = r
                best_cand = comp
        if best_cand is None or best_cand_r >= cur_r:
            continue
        cur = best_cand
        cur_r = best_cand_r
        improvements += 1
        best_r = min(best_r, cur_r)
        if cur_r < 23:
            (args.out / "solution.json").write_text(json.dumps(cur, indent=2), encoding="utf-8")
            break
    summary = {
        "steps": args.steps,
        "batch": args.batch,
        "start_rank": start_r,
        "final_rank": cur_r,
        "best_rank": best_r,
        "improvements": improvements,
        "improved": best_r < 23,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_r < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
