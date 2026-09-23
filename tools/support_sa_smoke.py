#!/usr/bin/env python3
"""SA on Stapleton support via random 2-edit moves (Brent-ok only)."""

from __future__ import annotations

import argparse
import json
import math
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


def two_edit(data, rng):
    d = deepcopy(data)
    pos = list(positions(*mats(d)))
    if len(pos) < 2:
        return d
    p1, p2 = rng.sample(pos, 2)
    for p in (p1, p2):
        v = getv(d, *p)
        opts = [x for x in TERN if x != v]
        if opts:
            setv(d, *p, rng.choice(opts))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=890002)
    ap.add_argument("--t0", type=float, default=4.0)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-support-sa-smoke"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    base, _ = exhaustive_zero(deepcopy(base))
    cur = deepcopy(base)
    cur_s = support(*mats(cur))
    best = deepcopy(cur)
    best_s = cur_s
    rng = random.Random(args.seed)
    t0 = time.time()
    accepted = uphill = 0
    for step in range(1, args.steps + 1):
        T = args.t0 * (0.02 / args.t0) ** (step / args.steps)
        trial = two_edit(cur, rng)
        if not brent_ok(*mats(trial)):
            continue
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        delta = s - cur_s
        if delta < 0 or (T > 1e-9 and rng.random() < math.exp(-delta / T)):
            accepted += 1
            if delta > 0:
                uphill += 1
            cur, cur_s = trial, s
            if s < best_s:
                best_s = s
                best = deepcopy(cur)
    summary = {
        "start_support": support(*mats(base)),
        "best_support": best_s,
        "accepted": accepted,
        "uphill_accepts": uphill,
        "steps": args.steps,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_s < 152:
        (args.out / "solution.json").write_text(
            json.dumps(best, separators=(",", ":")), encoding="utf-8"
        )
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
