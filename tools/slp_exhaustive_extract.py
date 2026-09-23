#!/usr/bin/env python3
"""Exhaustive common_pair extract on every side of a Sun SLP certificate."""

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

from slp_w_mutate import compact_side, cost, expand, matches_gold, normalize_final  # noqa: E402


def total_cost(sides):
    return cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"])


def try_extract_key(side, key, locs):
    i, j, ci, cj = key
    if abs(ci) != 1 or abs(cj) != 1:
        return None
    s_inter = cj // ci
    trial = deepcopy(side)
    new_idx = trial["base_dim"] + len(trial["inter"])
    trial["inter"].append((i, s_inter, j))
    for fi, ii, jj, sai, saj in locs:
        f = trial["final"][fi]
        nf = []
        removed_i = removed_j = False
        for idx, c in f:
            if not removed_i and idx == ii and c == sai:
                removed_i = True
                continue
            if not removed_j and idx == jj and c == saj:
                removed_j = True
                continue
            nf.append((idx, c))
        if not (removed_i and removed_j):
            return None
        nf.append((new_idx, sai))
        trial["final"][fi] = normalize_final(nf)
    return compact_side(trial) or trial


def pair_candidates(side):
    pair_locations = {}
    for fi, f in enumerate(side["final"]):
        if len(f) < 2:
            continue
        for (i, ci), (j, cj) in combinations(f, 2):
            if i == j:
                continue
            if i < j:
                key = (i, j, ci, cj)
                loc = (fi, i, j, ci, cj)
            else:
                key = (j, i, cj, ci)
                loc = (fi, j, i, cj, ci)
            pair_locations.setdefault(key, []).append(loc)
    return [(k, v) for k, v in pair_locations.items() if len(v) >= 2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-exhaust-extract"))
    ap.add_argument("--log", type=Path, default=Path("logs/exhaust-extract-cycle70.log"))
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
    tried = 0
    for name in ("U", "V", "W"):
        cands = pair_candidates(sides[name])
        for key, locs in cands:
            tried += 1
            cand = try_extract_key(sides[name], key, locs)
            if cand is None or not matches_gold(cand, golds[name]):
                continue
            trial = deepcopy(sides)
            trial[name] = cand
            tot = total_cost(trial)
            hits.append({"side": name, "key": key, "n_finals": len(locs), "total": tot})
            if tot < best:
                best = tot
                log(f"gold_ok extract {name} total={tot} key={key}")

    summary = {
        "start_total": start,
        "best_total": best,
        "candidates_tried": tried,
        "gold_preserving": len(hits),
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
