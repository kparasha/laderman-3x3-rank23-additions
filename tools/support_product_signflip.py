#!/usr/bin/env python3
"""Try flipping signs of one full product at a time (Brent symmetry)."""

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

from support_overnight import brent_ok, exhaustive_zero, mats, orbit_seeds, support, write_out  # noqa: E402


def flip_product(data, t):
    d = deepcopy(data)
    for name in ("u", "v", "w"):
        d[name][t] = [-x for x in d[name][t]]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-prod-flip"))
    ap.add_argument("--log", type=Path, default=Path("logs/prod-flip-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    orb = orbit_seeds(base)
    orb.sort(key=lambda x: x[0])
    best, _ = exhaustive_zero(deepcopy(orb[0][2]))
    best_s = support(*mats(best))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start support={best_s} rank={len(best['u'])}")
    t0 = time.time()
    for t in range(len(best["u"])):
        trial = flip_product(best, t)
        if not brent_ok(*mats(trial)):
            log(f"WARN flip t={t} brent fail")
            continue
        trial, _ = exhaustive_zero(trial)
        s = support(*mats(trial))
        if s < best_s:
            log(f"IMPROVED flip t={t} {best_s}->{s}")
            best_s = s
            best = trial
            write_out(args.out, best, {"flip_product": t, "improved": True})

    summary = {
        "best_support": best_s,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
