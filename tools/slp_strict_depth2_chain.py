#!/usr/bin/env python3
"""Two consecutive strict gold-preserving mutates; min certified total."""

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

from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import SIDES0, expand, matches_gold, mutate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=1030002)
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-strict-depth2-chain")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    start = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(start[n])[0] for n in ("U", "V", "W")}
    rng = random.Random(args.seed)
    t0 = time.time()
    start_c = total_cost(start)
    best = start_c
    for _ in range(args.chains):
        trial = deepcopy(start)
        ok = True
        for _ in range(2):
            name = rng.choice(("U", "V", "W"))
            cand, _ = mutate(trial[name], golds[name], rng)
            if cand is None or not matches_gold(cand, golds[name]):
                ok = False
                break
            trial[name] = cand
        if ok:
            best = min(best, total_cost(trial))
    summary = {
        "start": start_c,
        "best": best,
        "chains": args.chains,
        "beats56": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
