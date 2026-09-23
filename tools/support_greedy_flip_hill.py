#!/usr/bin/env python3
"""Greedy support descent: each step pick best Brent=0 flip among batch samples."""

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

from flipgraph_search import brent_residual, flip  # noqa: E402
from support_overnight import exhaustive_zero, mats  # noqa: E402
from support_overnight import support as count_support  # noqa: E402


def support_of(data):
    lifted, _ = exhaustive_zero(deepcopy(data))
    return count_support(*mats(lifted))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--batch", type=int, default=48)
    ap.add_argument("--seed", type=int, default=1150001)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-support-greedy-flip-115")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cur = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    start_s = support_of(cur)
    best_s = start_s
    cur_s = start_s
    improvements = 0
    plateau = 0
    for _ in range(args.steps):
        best_cand = None
        best_cand_s = cur_s
        for _ in range(args.batch):
            trial = flip(cur, rng)
            if brent_residual(trial["u"], trial["v"], trial["w"]) != 0:
                continue
            s = support_of(trial)
            if s < best_cand_s:
                best_cand_s = s
                best_cand = trial
        if best_cand is None or best_cand_s >= cur_s:
            plateau += 1
            continue
        cur = best_cand
        cur_s = best_cand_s
        improvements += 1
        best_s = min(best_s, cur_s)
        if cur_s < 152:
            (args.out / "solution.json").write_text(
                json.dumps(cur, indent=2), encoding="utf-8"
            )
            break
    summary = {
        "steps": args.steps,
        "batch": args.batch,
        "start_support": start_s,
        "final_support": cur_s,
        "best_support": best_s,
        "improvements": improvements,
        "plateau_steps": plateau,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
