#!/usr/bin/env python3
"""Sampled zero+sign-flip pairs on Stapleton (pair-zero was all-zero only).

  python3 -u tools/support_zero_flip.py --samples 80000 --seed 8812
"""

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
    write_out,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-zero-flip"))
    ap.add_argument("--log", type=Path, default=Path("logs/zero-flip-director.log"))
    ap.add_argument("--samples", type=int, default=80_000)
    ap.add_argument("--seed", type=int, default=8812)
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    orb = orbit_seeds(base)
    orb.sort(key=lambda x: x[0])
    best, _ = exhaustive_zero(deepcopy(orb[0][2]))
    best_s = support(*mats(best))
    pos = positions(*mats(best))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start support={best_s} positions={len(pos)} samples={args.samples}")
    rng = random.Random(args.seed)
    hits = 0
    t0 = time.time()
    for n in range(args.samples):
        p, q = rng.sample(pos, 2)
        old_q = getv(best, q[0], q[1], q[2])
        if old_q == 0:
            continue
        trial = deepcopy(best)
        setv(trial, p[0], p[1], p[2], 0)
        setv(trial, q[0], q[1], q[2], -old_q)
        if not brent_ok(*mats(trial)):
            continue
        hits += 1
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best_s:
            log(f"IMPROVED n={n} {best_s}->{s}")
            best_s = s
            best = trial
            write_out(args.out, best, {"note": f"zero-flip n={n}", "improved": True})
            if best_s <= 151:
                break
        if (n + 1) % 20000 == 0:
            log(f"status n={n+1} best={best_s} hits={hits} elapsed={time.time()-t0:.1f}s")

    summary = {
        "best_support": best_s,
        "improved": best_s < 152,
        "brent_hits": hits,
        "samples": args.samples,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
