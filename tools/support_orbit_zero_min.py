#!/usr/bin/env python3
"""Min support after exhaustive_zero over tensor symmetry orbit."""

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

from support_overnight import exhaustive_zero, mats, orbit_seeds, support  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-orbit-zero-min"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    t0 = time.time()
    orb = orbit_seeds(base)
    best = 10**9
    best_tag = None
    for s0, tag, data in orb:
        lifted, _ = exhaustive_zero(deepcopy(data))
        s = support(*mats(lifted))
        if s < best:
            best = s
            best_tag = tag
    summary = {
        "orbit_size": len(orb),
        "best_support": best,
        "best_tag": best_tag,
        "improved": best < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
