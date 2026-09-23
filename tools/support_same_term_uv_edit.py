#!/usr/bin/env python3
"""Two edits on same rank-1 term (one U cell, one V cell); Brent + support."""

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

from support_overnight import brent_ok, exhaustive_zero, getv, mats, setv, support  # noqa: E402

TERN = (-1, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=940002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-same-term-uv-edit")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    rank = len(base["u"])
    rng = random.Random(args.seed)
    t0 = time.time()
    best = support(*mats(base))
    hits = 0
    for _ in range(args.samples):
        t = rng.randrange(rank)
        i, j = rng.randrange(9), rng.randrange(9)
        trial = deepcopy(base)
        for name, idx in (("u", i), ("v", j)):
            v = getv(trial, name, t, idx)
            opts = [x for x in TERN if x != v]
            if opts:
                setv(trial, name, t, idx, rng.choice(opts))
        if not brent_ok(*mats(trial)):
            continue
        hits += 1
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best:
            best = s
    summary = {
        "samples": args.samples,
        "brent_hits": hits,
        "best_support": best,
        "improved": best < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
