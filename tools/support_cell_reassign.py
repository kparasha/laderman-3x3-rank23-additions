#!/usr/bin/env python3
"""Exhaustive 1-cell ternary reassignment on Stapleton (not zero-only).

  python3 -u tools/support_cell_reassign.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from support_overnight import brent_ok, exhaustive_zero, getv, mats, orbit_seeds, positions, setv, support, write_out  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-cell-reassign"))
    ap.add_argument("--log", type=Path, default=Path("logs/cell-reassign-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
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

    log(f"start support={best_s} cells={len(pos)}")
    t0 = time.time()
    brent_hits = 0
    tried = 0
    for name, t, i in pos:
        old = getv(best, name, t, i)
        for nv in (-1, 0, 1):
            if nv == old:
                continue
            tried += 1
            trial = deepcopy(best)
            setv(trial, name, t, i, nv)
            if not brent_ok(*mats(trial)):
                continue
            brent_hits += 1
            trial, _ = exhaustive_zero(trial)
            s = support(*mats(trial))
            if s < best_s:
                log(f"IMPROVED {name}[{t},{i}] {old}->{nv} support {best_s}->{s}")
                best_s = s
                best = trial
                write_out(args.out, best, {"improved": True})
                if best_s <= 151:
                    break
        if best_s <= 151:
            break

    summary = {
        "best_support": best_s,
        "improved": best_s < 152,
        "tried": tried,
        "brent_ok": brent_hits,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
