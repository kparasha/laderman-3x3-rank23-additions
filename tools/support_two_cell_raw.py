#!/usr/bin/env python3
"""Two-cell reassign: track support before vs after greedy zero (Stapleton)."""

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

from support_overnight import (  # noqa: E402
    brent_ok,
    exhaustive_zero,
    getv,
    mats,
    orbit_seeds,
    positions,
    setv,
    support,
)

TERN = (-1, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=730001)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-two-cell-raw"))
    ap.add_argument("--log", type=Path, default=Path("logs/two-cell-raw-cycle73.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    orb = orbit_seeds(base)
    orb.sort(key=lambda x: x[0])
    best, _ = exhaustive_zero(deepcopy(orb[0][2]))
    start_s = support(*mats(best))
    pos = positions(*mats(best))
    rng = random.Random(args.seed)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start lifted_support={start_s} samples={args.samples}")
    t0 = time.time()
    brent_hits = 0
    best_raw = start_s
    best_lift = start_s

    for n in range(1, args.samples + 1):
        if len(pos) < 2:
            break
        (n1, t1, i1), (n2, t2, i2) = rng.sample(pos, 2)
        v1, v2 = getv(best, n1, t1, i1), getv(best, n2, t2, i2)
        opts1 = [x for x in TERN if x != v1]
        opts2 = [x for x in TERN if x != v2]
        if not opts1 or not opts2:
            continue
        trial = deepcopy(best)
        setv(trial, n1, t1, i1, rng.choice(opts1))
        setv(trial, n2, t2, i2, rng.choice(opts2))
        if not brent_ok(*mats(trial)):
            continue
        brent_hits += 1
        raw = support(*mats(trial))
        lifted, _ = exhaustive_zero(deepcopy(trial))
        lift = support(*mats(lifted))
        if raw < best_raw:
            best_raw = raw
            log(f"raw_improved n={n} support={raw}")
        if lift < best_lift:
            best_lift = lift
            log(f"lift_improved n={n} support={lift}")

    summary = {
        "start_support": start_s,
        "best_raw_support": best_raw,
        "best_lift_support": best_lift,
        "improved": best_lift < 152,
        "brent_hits": brent_hits,
        "samples": args.samples,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_lift < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
