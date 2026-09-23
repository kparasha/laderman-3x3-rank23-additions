#!/usr/bin/env python3
"""Exhaustive shorten_one_final on each multi-ref final (all sides)."""

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

from slp_w_mutate import cost, expand, matches_gold, normalize_final  # noqa: E402


def total_cost(sides):
    return cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"])


def shorten_final_exhaust(side, gold, fi):
    _, vs = expand(side)
    target = gold[fi]
    dim = len(target)
    n = len(vs)
    best = None
    best_len = len(side["final"][fi])

    for i in range(n):
        for sa in (1, -1):
            g = tuple(sa * vs[i][k] for k in range(dim))
            if g == target:
                nf = [(i, sa)]
                if len(nf) < best_len:
                    best_len, best = len(nf), nf

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            for sa in (1, -1):
                for sb in (1, -1):
                    g = tuple(sa * vs[i][k] + sb * vs[j][k] for k in range(dim))
                    if g == target:
                        nf = normalize_final([(i, sa), (j, sb)])
                        if len(nf) < best_len:
                            best_len, best = len(nf), nf

    if best is None or best_len >= len(side["final"][fi]):
        return None
    s2 = deepcopy(side)
    s2["final"][fi] = best
    return s2 if matches_gold(s2, gold) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-exhaust-shorten"))
    ap.add_argument("--log", type=Path, default=Path("logs/exhaust-shorten-cycle71.log"))
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
        multi = [fi for fi, f in enumerate(side["final"]) if len(f) >= 2]
        for fi in multi:
            cand = shorten_final_exhaust(side, golds[name], fi)
            if cand is None:
                continue
            trial = deepcopy(sides)
            trial[name] = cand
            tot = total_cost(trial)
            hits.append({"side": name, "final": fi, "total": tot})
            if tot < best:
                best = tot
                log(f"gold_ok shorten {name}[{fi}] total={tot}")

    summary = {
        "start_total": start,
        "best_total": best,
        "gold_shortens": len(hits),
        "improved": best < 56,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(
        json.dumps({**summary, "hits": hits}, indent=2), encoding="utf-8"
    )
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
