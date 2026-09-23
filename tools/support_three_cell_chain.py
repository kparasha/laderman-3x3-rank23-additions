#!/usr/bin/env python3
"""From Brent-ok 2-cell edits, exhaust third-cell ternary reassign (support<152).

Two-cell random search found brent_hits=24 but zero-greedy stayed 152; a third
coordinated cell may enable lower support.

  python3 -u tools/support_three_cell_chain.py --two-cell-tries 80000 --max-chains 400
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

from support_overnight import brent_ok, exhaustive_zero, getv, mats, orbit_seeds, positions, setv, support, write_out  # noqa: E402

TERN = (-1, 0, 1)


def try_two_cell(best, pos, rng):
    if len(pos) < 2:
        return None
    (n1, t1, i1), (n2, t2, i2) = rng.sample(pos, 2)
    v1, v2 = getv(best, n1, t1, i1), getv(best, n2, t2, i2)
    opts1 = [x for x in TERN if x != v1]
    opts2 = [x for x in TERN if x != v2]
    if not opts1 or not opts2:
        return None
    trial = deepcopy(best)
    setv(trial, n1, t1, i1, rng.choice(opts1))
    setv(trial, n2, t2, i2, rng.choice(opts2))
    if not brent_ok(*mats(trial)):
        return None
    return trial


def exhaust_third(base, pos):
    best_s = support(*mats(base))
    best_lift = base
    used = set()
    for name, t, i in pos:
        cur = getv(base, name, t, i)
        for nv in TERN:
            if nv == cur:
                continue
            trial = deepcopy(base)
            setv(trial, name, t, i, nv)
            if not brent_ok(*mats(trial)):
                continue
            lifted, _ = exhaustive_zero(deepcopy(trial))
            s = support(*mats(lifted))
            if s < best_s:
                best_s = s
                best_lift = lifted
    return best_s, best_lift


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--two-cell-tries", type=int, default=80_000)
    ap.add_argument("--max-chains", type=int, default=400)
    ap.add_argument("--seed", type=int, default=401001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-three-cell-chain"))
    ap.add_argument("--log", type=Path, default=Path("logs/three-cell-chain-director.log"))
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

    log(f"start support={start_s} two_cell_tries={args.two_cell_tries} max_chains={args.max_chains}")
    t0 = time.time()
    chains = 0
    best_s = start_s
    best_state = best

    for n in range(1, args.two_cell_tries + 1):
        if chains >= args.max_chains:
            break
        mid = try_two_cell(best, pos, rng)
        if mid is None:
            continue
        chains += 1
        s3, lifted = exhaust_third(mid, pos)
        if s3 < best_s:
            best_s = s3
            best_state = lifted
            log(f"IMPROVED chain={chains} try={n} support={s3}")
            write_out(args.out, best_state, {"note": f"chain={chains}", "improved": True})

    summary = {
        "start_support": start_s,
        "best_support": best_s,
        "improved": best_s < 152,
        "two_cell_chains": chains,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
