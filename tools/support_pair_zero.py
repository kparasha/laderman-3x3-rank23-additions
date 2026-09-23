#!/usr/bin/env python3
"""Exhaustive simultaneous pair-zero on Stapleton orbit (escape 152).

Single-zero greedy is already in support_overnight; Brent may require two
entries cleared together before identities still close.

  python3 -u tools/support_pair_zero.py --out submissions/director-agentic-pair-zero
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from itertools import combinations
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


def pair_zero_pass(data, max_pairs=None):
    """Try zeroing every pair of nonzero entries; then re-run single-zero."""
    best = deepcopy(data)
    best_s = support(*mats(best))
    pos = positions(*mats(best))
    pairs = list(combinations(pos, 2))
    if max_pairs is not None:
        pairs = pairs[:max_pairs]
    tried = hits = 0
    for p1, p2 in pairs:
        tried += 1
        trial = deepcopy(best)
        setv(trial, p1[0], p1[1], p1[2], 0)
        setv(trial, p2[0], p2[1], p2[2], 0)
        if not brent_ok(*mats(trial)):
            continue
        hits += 1
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best_s:
            best_s = s
            best = trial
            if best_s <= 151:
                return best, best_s, tried, hits
    return best, best_s, tried, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-pair-zero"))
    ap.add_argument("--log", type=Path, default=Path("logs/pair-zero-director.log"))
    ap.add_argument("--max-orbit", type=int, default=0, help="0 = all orbit seeds")
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    assert brent_ok(*mats(base))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    orb = orbit_seeds(base)
    if args.max_orbit > 0:
        orb = orb[: args.max_orbit]

    global_best = deepcopy(orb[0][2])
    global_best, _ = exhaustive_zero(global_best)
    global_s = support(*mats(global_best))
    log(f"start orbit={len(orb)} baseline_support={global_s}")

    t0 = time.time()
    for idx, (s0, tag, seed_data) in enumerate(orb):
        lifted, _ = exhaustive_zero(deepcopy(seed_data))
        best, s, tried, hits = pair_zero_pass(lifted)
        if s < global_s:
            log(f"IMPROVED orbit[{idx}] tag={tag} {global_s}->{s} tried={tried} hits={hits}")
            global_s = s
            global_best = best
            write_out(args.out, global_best, {"note": f"pair-zero {tag}", "improved": True})
            if global_s <= 151:
                break

    elapsed = time.time() - t0
    summary = {
        "best_support": global_s,
        "improved": global_s < 152,
        "orbit_seeds": len(orb),
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if global_s < 152:
        write_out(args.out, global_best, {"note": "final", "improved": True})
    return 0 if global_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
