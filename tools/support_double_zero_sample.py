#!/usr/bin/env python3
"""Random pair of cell zeros on Stap; Brent check; min lifted support."""

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

from search_support import brent_ok, get, mats, positions, setv  # noqa: E402
from support_overnight import exhaustive_zero  # noqa: E402
from support_overnight import support as count_support  # noqa: E402


def support_lifted(data):
    lifted, _ = exhaustive_zero(deepcopy(data))
    return count_support(*mats(lifted))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=1800)
    ap.add_argument("--seed", type=int, default=1200003)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-support-double-zero-120")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    t0 = time.time()
    start_s = support_lifted(base)
    best_s = start_s
    brent_hits = 0
    for _ in range(args.samples):
        cur = deepcopy(base)
        pos = positions(*mats(cur))
        if len(pos) < 2:
            break
        (n1, t1, i1), (n2, t2, i2) = rng.sample(pos, 2)
        if (n1, t1, i1) == (n2, t2, i2):
            continue
        setv(cur, n1, t1, i1, 0)
        setv(cur, n2, t2, i2, 0)
        if not brent_ok(*mats(cur)):
            continue
        brent_hits += 1
        best_s = min(best_s, support_lifted(cur))
        if best_s < 152:
            (args.out / "solution.json").write_text(json.dumps(cur, indent=2), encoding="utf-8")
            break
    summary = {
        "samples": args.samples,
        "start_support": start_s,
        "best_support": best_s,
        "brent_hits": brent_hits,
        "improved": best_s < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
