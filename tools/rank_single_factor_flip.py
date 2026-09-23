#!/usr/bin/env python3
"""Single-factor sign flip on one rank-1 product (U-only / V-only / W-only).

Whole-product flip breaks Brent on Stapleton; single-factor edits change the
tensor and may stay Brent-ok, then term drop could yield exact rank < 23.

  python3 -u tools/rank_single_factor_flip.py submissions/sun56/solution.json
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

from support_overnight import brent_ok, support  # noqa: E402


def flip_one(data, t: int, factor: str):
    d = deepcopy(data)
    d[factor][t] = [-x for x in d[factor][t]]
    return d


def drop_term(data, t: int):
    d = deepcopy(data)
    for name in ("u", "v", "w"):
        d[name] = [row for i, row in enumerate(d[name]) if i != t]
    return d


def scan(data):
    rank = len(data["u"])
    hits = []
    for t in range(rank):
        for fac in ("u", "v", "w"):
            flipped = flip_one(data, t, fac)
            if not brent_ok(*[flipped[k] for k in ("u", "v", "w")]):
                continue
            dropped = drop_term(flipped, t)
            r2 = len(dropped["u"])
            ok2 = brent_ok(*[dropped[k] for k in ("u", "v", "w")])
            hits.append(
                {
                    "t": t,
                    "factor": fac,
                    "flip_brent": True,
                    "drop_rank": r2,
                    "drop_brent": ok2,
                    "support_after_flip": support(*[flipped[k] for k in ("u", "v", "w")]),
                }
            )
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-single-factor-flip"))
    ap.add_argument("--log", type=Path, default=Path("logs/single-factor-flip-cycle66.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    all_results = {}
    best_rank = 23
    for src in args.src:
        data = json.loads(src.read_text(encoding="utf-8"))
        hits = scan(data)
        brent_flips = len(hits)
        rank22 = sum(1 for h in hits if h["drop_brent"])
        log(f"{src.name}: flip_brent_hits={brent_flips} drop_brent_rank22={rank22}")
        all_results[str(src)] = hits
        if rank22 and best_rank > 22:
            best_rank = 22

    summary = {
        "schemes": list(all_results.keys()),
        "best_rank": best_rank,
        "improved": best_rank < 23,
        "elapsed_s": time.time() - t0,
        "details": {k: len(v) for k, v in all_results.items()},
    }
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.out / "hits.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    log(f"done {json.dumps(summary)}")
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
