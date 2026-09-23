#!/usr/bin/env python3
"""Sampled 3-cell cyclic value rotation on Stapleton (a->b->c->a).

  python3 -u tools/support_three_cell_rotate.py --samples 40000 --seed 640001
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


def rotate3(data, p1, p2, p3):
    trial = deepcopy(data)
    v1, v2, v3 = getv(trial, *p1), getv(trial, *p2), getv(trial, *p3)
    setv(trial, *p1, v3)
    setv(trial, *p2, v1)
    setv(trial, *p3, v2)
    return trial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--samples", type=int, default=40_000)
    ap.add_argument("--seed", type=int, default=640001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-three-cell-rotate"))
    ap.add_argument("--log", type=Path, default=Path("logs/three-cell-rotate-cycle64.log"))
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

    log(f"start support={start_s} cells={len(pos)} samples={args.samples}")
    t0 = time.time()
    brent_hits = 0
    best_s = start_s
    best_data = best

    for n in range(1, args.samples + 1):
        if len(pos) < 3:
            break
        p1, p2, p3 = rng.sample(pos, 3)
        if len({getv(best_data, *p) for p in (p1, p2, p3)}) < 2:
            continue
        trial = rotate3(best_data, p1, p2, p3)
        if not brent_ok(*mats(trial)):
            continue
        brent_hits += 1
        lifted, _ = exhaustive_zero(trial)
        s = support(*mats(lifted))
        if s < best_s:
            best_s = s
            best_data = lifted
            log(f"IMPROVED sample={n} support={s}")

    summary = {
        "start_support": start_s,
        "best_support": best_s,
        "improved": best_s < 152,
        "samples": args.samples,
        "brent_hits": brent_hits,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
