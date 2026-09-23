#!/usr/bin/env python3
"""Exhaustive single drop_inter on each side of a Sun (or any) SLP certificate."""

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

from slp_w_mutate import SIDES0, cost, expand, matches_gold, try_drop_random_inter  # noqa: E402


def total_cost(sides):
    return cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"])


def drop_inter_at(side, gold, k):
    class R:
        pass

    rng = R()
    rng.randrange = lambda n: k  # type: ignore
    return try_drop_random_inter(side, gold, rng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-exhaust-drop-inter"))
    ap.add_argument("--log", type=Path, default=Path("logs/exhaust-drop-inter-cycle69.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    start = total_cost(sides)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    best = start
    hits = []
    for name in ("U", "V", "W"):
        side = sides[name]
        n = len(side["inter"])
        for k in range(n):
            cand = drop_inter_at(side, golds[name], k)
            if cand is None or not matches_gold(cand, golds[name]):
                continue
            trial = deepcopy(sides)
            trial[name] = cand
            tot = total_cost(trial)
            hits.append({"side": name, "inter_k": k, "total": tot})
            if tot < best:
                best = tot
                log(f"gold_ok drop {name}[{k}] total={tot}")

    summary = {
        "start_total": start,
        "best_total": best,
        "gold_preserving_drops": len(hits),
        "improved": best < 56,
        "hits": hits,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps({k: summary[k] for k in summary if k != 'hits'})}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
