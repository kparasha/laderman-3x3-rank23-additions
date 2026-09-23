#!/usr/bin/env python3
"""Two random ternary edits on Sun56 — Brent + support (not Stapleton orbit)."""

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

from support_overnight import brent_ok, getv, mats, positions, setv, support  # noqa: E402

TERN = (-1, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=750001)
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun-two-edit"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    start = support(*mats(data))
    pos = [p for p in positions(*mats(data))]
    rng = random.Random(args.seed)
    t0 = time.time()
    brent_hits = 0
    best = start

    for _ in range(args.samples):
        if len(pos) < 2:
            break
        p1, p2 = rng.sample(pos, 2)
        trial = deepcopy(data)
        for p in (p1, p2):
            v = getv(trial, *p)
            opts = [x for x in TERN if x != v]
            if opts:
                setv(trial, *p, rng.choice(opts))
        if not brent_ok(*mats(trial)):
            continue
        brent_hits += 1
        s = support(*mats(trial))
        best = min(best, s)

    summary = {
        "start_support": start,
        "best_support": best,
        "brent_hits": brent_hits,
        "samples": args.samples,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
