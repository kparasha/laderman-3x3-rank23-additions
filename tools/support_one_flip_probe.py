#!/usr/bin/env python3
"""Random single-coefficient flips from Stapleton@152; Brent-ok + greedy zero support."""

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


def one_flip(data, rng):
    d = deepcopy(data)
    pos = positions(*mats(d))
    name, t, i = rng.choice(pos)
    v = getv(d, name, t, i)
    opts = [x for x in TERN if x != v]
    setv(d, name, t, i, rng.choice(opts))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=840002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-one-flip-support")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    start = support(*mats(base))
    rng = random.Random(args.seed)
    t0 = time.time()
    brent_hits = 0
    best = start

    for _ in range(args.samples):
        trial = one_flip(base, rng)
        if not brent_ok(*mats(trial)):
            continue
        brent_hits += 1
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best:
            best = s

    summary = {
        "start_support": start,
        "best_support": best,
        "brent_hits": brent_hits,
        "samples": args.samples,
        "improved": best < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
