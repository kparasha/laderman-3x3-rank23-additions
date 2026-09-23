#!/usr/bin/env python3
"""Greedy 2-edit walk: accept if Brent-ok and raw support drops (before zero pass)."""

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

from support_overnight import brent_ok, exhaustive_zero, getv, mats, positions, setv, support  # noqa: E402

TERN = (-1, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=920002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-support-raw-hill"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cur = json.loads(args.src.read_text(encoding="utf-8"))
    cur, _ = exhaustive_zero(deepcopy(cur))
    best_lift = support(*mats(cur))
    best = deepcopy(cur)
    rng = random.Random(args.seed)
    t0 = time.time()
    raw_improve = brent_hits = 0
    for _ in range(args.steps):
        pos = list(positions(*mats(cur)))
        if len(pos) < 2:
            break
        p1, p2 = rng.sample(pos, 2)
        trial = deepcopy(cur)
        for p in (p1, p2):
            v = getv(trial, *p)
            opts = [x for x in TERN if x != v]
            if opts:
                setv(trial, *p, rng.choice(opts))
        if not brent_ok(*mats(trial)):
            continue
        brent_hits += 1
        raw = support(*mats(trial))
        if raw < support(*mats(cur)):
            raw_improve += 1
            cur = trial
        lifted, _ = exhaustive_zero(deepcopy(cur))
        s = support(*mats(lifted))
        if s < best_lift:
            best_lift = s
            best = lifted
    summary = {
        "start_lift": support(*mats(json.loads(args.src.read_text()))),
        "best_lift_support": best_lift,
        "brent_hits": brent_hits,
        "raw_improve_steps": raw_improve,
        "improved": best_lift < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_lift < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
