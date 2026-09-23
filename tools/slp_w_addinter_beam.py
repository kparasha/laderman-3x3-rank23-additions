#!/usr/bin/env python3
"""Beam search on Sun W using add_inter moves (+ extract/shorten/compact).

Prior W beam (extract-only) expanded 1 state from Sun W. This adds the
add_inter/drop_inter move class from slp_w_mutate (requires ≥2 finals shorter).

  python3 -u tools/slp_w_addinter_beam.py --max-states 15000 --max-depth 4 \\
      --out submissions/director-agentic-w-addinter
"""

from __future__ import annotations

import argparse
import heapq
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_beam import enum_extract_common_pair, enum_shorten_two_term, side_key  # noqa: E402
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


def enum_add_inter_shorten_two(side, gold):
    _, vs = expand(side)
    n = len(vs)
    dim = len(gold[0])
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            for sign in (1, -1):
                trial = deepcopy(side)
                new_idx = trial["base_dim"] + len(trial["inter"])
                trial["inter"].append((a, sign, b))
                _, vs2 = expand(trial)
                improved = 0
                new_finals = []
                vnew = vs2[new_idx]
                for fi, f in enumerate(trial["final"]):
                    target = gold[fi]
                    old_len = len(f)
                    found = None
                    if vnew == target:
                        found = [(new_idx, 1)]
                    elif tuple(-x for x in vnew) == target:
                        found = [(new_idx, -1)]
                    else:
                        for i in range(len(vs2)):
                            if i == new_idx:
                                continue
                            for sa in (1, -1):
                                for sb in (1, -1):
                                    g = tuple(
                                        sa * vnew[k] + sb * vs2[i][k]
                                        for k in range(dim)
                                    )
                                    if g == target:
                                        found = normalize_final([(new_idx, sa), (i, sb)])
                                        break
                                if found:
                                    break
                            if found:
                                break
                    if found and len(found) < old_len:
                        new_finals.append(found)
                        improved += 1
                    else:
                        new_finals.append(f)
                if improved < 2:
                    continue
                trial["final"] = new_finals
                trial = compact_side(trial) or trial
                if matches_gold(trial, gold):
                    yield trial


def enum_drop_inters(side, gold):
    if not side["inter"]:
        return
    base = side["base_dim"]
    for k in range(len(side["inter"])):
        drop_idx = base + k
        new_inter = []
        ok = True
        for t, (a, sgn, b) in enumerate(side["inter"]):
            if t == k:
                continue

            def map_i(x):
                if x == drop_idx:
                    return None
                return x - 1 if x > drop_idx else x

            a2, b2 = map_i(a), map_i(b)
            if a2 is None or b2 is None:
                ok = False
                break
            new_inter.append((a2, sgn, b2))
        if not ok:
            continue
        new_finals = []
        bad = False
        for f in side["final"]:
            nf = []
            for idx, c in f:
                if idx == drop_idx:
                    bad = True
                    break
                nf.append((idx - 1 if idx > drop_idx else idx, c))
            if bad:
                break
            new_finals.append(normalize_final(nf))
        if bad:
            continue
        trial = {"base_dim": base, "inter": new_inter, "final": new_finals}
        if matches_gold(trial, gold):
            yield trial


def neighbors(side, gold):
    seen = set()
    for gen in (
        enum_extract_common_pair(side),
        enum_shorten_two_term(side, gold),
        enum_add_inter_shorten_two(side, gold),
        enum_drop_inters(side, gold),
    ):
        for cand in gen:
            if not matches_gold(cand, gold):
                continue
            k = side_key(cand)
            if k in seen:
                continue
            seen.add(k)
            comp = compact_side(cand)
            if comp and matches_gold(comp, gold):
                cand = comp
                k = side_key(cand)
            yield cand


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-states", type=int, default=15_000)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--max-cost", type=int, default=35)
    ap.add_argument("--log", type=Path, default=Path("logs/w-addinter-director.log"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-w-addinter")
    )
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
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

    n0 = len(list(neighbors(start, gold_w)))
    log(
        f"start W={best_c} neighbors={n0} max_states={args.max_states} "
        f"depth={args.max_depth}"
    )

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
                {"note": f"addinter beam d={depth}", "improved": best_c < 30},
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
        "start_neighbors": n0,
        "expanded": expanded,
        "visited": len(visited),
        "elapsed_s": elapsed,
        "brent_ok": brent_ok(*sun_uvw_hill(u_side, v_side, best)),
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
