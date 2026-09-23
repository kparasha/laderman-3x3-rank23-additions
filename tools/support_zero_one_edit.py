#!/usr/bin/env python3
"""One cell zeroed + another cell changed (sampled) on Stapleton support search."""

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
    ap.add_argument("--samples", type=int, default=25_000)
    ap.add_argument("--seed", type=int, default=660001)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-zero-one-edit"))
    ap.add_argument("--log", type=Path, default=Path("logs/zero-one-edit-cycle66.log"))
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

    log(f"start support={start_s} samples={args.samples}")
    t0 = time.time()
    brent_hits = 0
    best_s = start_s

    for n in range(1, args.samples + 1):
        if len(pos) < 2:
            break
        pz, pe = rng.sample(pos, 2)
        trial = deepcopy(best)
        old_z, old_e = getv(trial, *pz), getv(trial, *pe)
        setv(trial, *pz, 0)
        opts = [x for x in TERN if x != old_e]
        if not opts:
            continue
        setv(trial, *pe, rng.choice(opts))
        if not brent_ok(*mats(trial)):
            continue
        brent_hits += 1
        lifted, _ = exhaustive_zero(trial)
        s = support(*mats(lifted))
        if s < best_s:
            best_s = s
            log(f"IMPROVED n={n} support={s}")

    summary = {
        "start_support": start_s,
        "best_support": best_s,
        "brent_hits": brent_hits,
        "samples": args.samples,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
