#!/usr/bin/env python3
"""Exhaustive k-zero on first N support positions (Stapleton orbit).

Random triple-zero: 120k samples, brent_ok_triples=0. This exhausts C(N,k)
patterns on a fixed small position list.

  python3 -u tools/support_exhaustive_kzero.py --k 4 --positions 18
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
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--positions", type=int, default=18, help="use first N nonzero entries")
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-kzero-exhaust"))
    ap.add_argument("--log", type=Path, default=Path("logs/kzero-exhaust-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    orb = orbit_seeds(base)
    orb.sort(key=lambda x: x[0])
    best, _ = exhaustive_zero(deepcopy(orb[0][2]))
    best_s = support(*mats(best))
    pos = positions(*mats(best))[: args.positions]
    combos = list(combinations(pos, args.k))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start support={best_s} k={args.k} pos={len(pos)} combos={len(combos)}")
    t0 = time.time()
    hits = 0
    for i, combo in enumerate(combos):
        trial = deepcopy(best)
        for name, t, j in combo:
            setv(trial, name, t, j, 0)
        if not brent_ok(*mats(trial)):
            continue
        hits += 1
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best_s:
            log(f"IMPROVED combo={i} {best_s}->{s}")
            best_s = s
            best = trial
            write_out(args.out, best, {"improved": True, "combo_index": i})
            if best_s <= 151:
                break
        if (i + 1) % 500 == 0:
            log(f"status i={i+1}/{len(combos)} best={best_s} brent_hits={hits}")

    summary = {
        "best_support": best_s,
        "improved": best_s < 152,
        "k": args.k,
        "combos": len(combos),
        "brent_ok": hits,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
