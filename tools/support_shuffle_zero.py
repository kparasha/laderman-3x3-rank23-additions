#!/usr/bin/env python3
"""Random-order single-zero passes on Stapleton (non-greedy exhaustive_zero)."""

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

from support_overnight import brent_ok, exhaustive_zero, getv, mats, orbit_seeds, positions, setv, support  # noqa: E402


def shuffle_pass(data, rng):
    cur = deepcopy(data)
    pos = list(positions(*mats(cur)))
    rng.shuffle(pos)
    improved = False
    for name, t, i in pos:
        old = getv(cur, name, t, i)
        if old == 0:
            continue
        setv(cur, name, t, i, 0)
        if brent_ok(*mats(cur)):
            improved = True
        else:
            setv(cur, name, t, i, old)
    return cur if improved else data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=300)
    ap.add_argument("--seed", type=int, default=810001)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-shuffle-zero"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    orb = orbit_seeds(base)
    orb.sort(key=lambda x: x[0])
    start, _ = exhaustive_zero(deepcopy(orb[0][2]))
    start_s = support(*mats(start))
    rng = random.Random(args.seed)
    t0 = time.time()
    best_s = start_s
    best = start

    for p in range(args.passes):
        trial = shuffle_pass(deepcopy(start), rng)
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best_s:
            best_s = s
            best = trial

    summary = {
        "start_support": start_s,
        "best_support": best_s,
        "passes": args.passes,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
