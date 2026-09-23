#!/usr/bin/env python3
"""Deterministic best-first beam on Sun W SLP (gold-preserving CSE moves).

Random W mutate/SA plateau at W=30; this explores the move graph with a
bounded beam (sorted pair-extracts + compact + exhaustive 2-term shorten).

  python3 -u tools/slp_w_beam.py --max-states 12000 --max-depth 6 \\
      --log logs/w-beam-director.log --out submissions/director-agentic-w-beam
"""

from __future__ import annotations

import argparse
import heapq
import json
import sys
import time
from copy import deepcopy
from itertools import combinations
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_mutate import (  # noqa: E402
    SIDES0,
    brent_ok,
    compact_side,
    cost,
    expand,
    matches_gold,
    normalize_final,
    sun_uvw_hill,
    write_best,
)


def side_key(side) -> str:
    return json.dumps(
        {"inter": side["inter"], "final": side["final"]},
        sort_keys=True,
        separators=(",", ":"),
    )


def enum_extract_common_pair(side):
    """All successful pair-extract moves (deterministic order)."""
    s = side
    pair_locations = {}
    for fi, f in enumerate(s["final"]):
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

    for key in sorted(pair_locations.keys()):
        locs = pair_locations[key]
        if len(locs) < 2:
            continue
        i, j, ci, cj = key
        if abs(ci) != 1 or abs(cj) != 1:
            continue
        s_inter = cj // ci
        trial = deepcopy(s)
        new_idx = trial["base_dim"] + len(trial["inter"])
        trial["inter"].append((i, s_inter, j))
        ok = True
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
                ok = False
                break
            nf.append((new_idx, sai))
            trial["final"][fi] = normalize_final(nf)
        if not ok:
            continue
        trial = compact_side(trial) or trial
        yield trial


def enum_shorten_two_term(side, gold):
    """Rewrite one multi-term final using any 2-term combo (deterministic)."""
    _, vs = expand(side)
    dim = len(gold[0])
    n = len(vs)
    multi = [fi for fi, f in enumerate(side["final"]) if len(f) >= 2]
    for fi in multi:
        target = gold[fi]
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    for sa in (1, -1):
                        g = tuple(sa * vs[i][k] for k in range(dim))
                        if g == target:
                            s2 = deepcopy(side)
                            s2["final"][fi] = [(i, sa)]
                            yield s2
                    continue
                for sa in (1, -1):
                    for sb in (1, -1):
                        g = tuple(
                            sa * vs[i][k] + sb * vs[j][k] for k in range(dim)
                        )
                        if g == target:
                            s2 = deepcopy(side)
                            s2["final"][fi] = normalize_final([(i, sa), (j, sb)])
                            yield s2


def neighbors(side, gold):
    seen = set()
    for cand in enum_extract_common_pair(side):
        if matches_gold(cand, gold):
            k = side_key(cand)
            if k not in seen:
                seen.add(k)
                yield cand
    comp = compact_side(side)
    if comp and matches_gold(comp, gold):
        k = side_key(comp)
        if k not in seen:
            seen.add(k)
            yield comp
    for cand in enum_shorten_two_term(side, gold):
        if matches_gold(cand, gold):
            k = side_key(cand)
            if k not in seen:
                seen.add(k)
                yield cand


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-states", type=int, default=12_000)
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--max-cost", type=int, default=33, help="explore up to this W cost")
    ap.add_argument("--log", type=Path, default=Path("logs/w-beam-director.log"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-w-beam"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    u_side = deepcopy(SIDES0["U"])
    v_side = deepcopy(SIDES0["V"])
    gold_w, _ = expand(SIDES0["W"])
    start = deepcopy(SIDES0["W"])
    base_uv = cost(u_side) + cost(v_side)

    best = deepcopy(start)
    best_c = cost(best)
    visited = {side_key(start)}

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start W={best_c} total={base_uv + best_c} max_states={args.max_states} "
        f"max_depth={args.max_depth} max_cost={args.max_cost}"
    )

    # (cost, depth, tie, side)
    heap = [(best_c, 0, 0, start)]
    tie = 1
    expanded = 0
    t0 = time.time()

    while heap and expanded < args.max_states:
        c, depth, _, side = heapq.heappop(heap)
        expanded += 1
        if c < best_c:
            best_c = c
            best = deepcopy(side)
            log(f"IMPROVED expand={expanded} depth={depth} W={best_c} total={base_uv + best_c}")
            write_best(
                args.out,
                best,
                u_side,
                v_side,
                {
                    "note": f"beam depth={depth}",
                    "improved": best_c < 30,
                    "baseline_W": 30,
                },
            )
            if best_c <= 29:
                break
        if depth >= args.max_depth:
            continue
        for cand in neighbors(side, gold_w):
            cc = cost(cand)
            if cc > args.max_cost:
                continue
            k = side_key(cand)
            if k in visited:
                continue
            visited.add(k)
            tie += 1
            heapq.heappush(heap, (cc, depth + 1, tie, cand))

    elapsed = time.time() - t0
    total = base_uv + best_c
    summary = {
        "W": best_c,
        "total": total,
        "improved": total < 56,
        "expanded": expanded,
        "visited": len(visited),
        "elapsed_s": elapsed,
        "brent_ok": brent_ok(*sun_uvw_hill(u_side, v_side, best)),
    }
    log(f"done {json.dumps(summary)}")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
