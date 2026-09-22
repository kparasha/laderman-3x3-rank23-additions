#!/usr/bin/env python3
"""Rank-drop search: start from a rank-23 scheme, delete products, repair residual.

Aim: residual 0 with fewer than 23 products (rank < 23).

  python3 -u tools/rank_drop_search.py submissions/stapleton60/solution.json \\
      submissions/director-rank-drop 101 20000
"""

from __future__ import annotations

import json
import random
import sys
import time
from copy import deepcopy
from pathlib import Path


def residual(u, v, w) -> int:
    bad = 0
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(len(u)))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                if s != int(inner == b_inner and c == 3 * col + row):
                    bad += 1
    return bad


def support(u, v, w) -> int:
    return sum(x != 0 for M in (u, v, w) for row in M for x in row)


def drop_product(data, t):
    d = {
        "u": [r[:] for i, r in enumerate(data["u"]) if i != t],
        "v": [r[:] for i, r in enumerate(data["v"]) if i != t],
        "w": [r[:] for i, r in enumerate(data["w"]) if i != t],
    }
    return d


def flip_entry(data, rng):
    d = deepcopy(data)
    name = rng.choice(["u", "v", "w"])
    M = d[name]
    t = rng.randrange(len(M))
    i = rng.randrange(9)
    M[t][i] = rng.choice([-1, 0, 1])
    return d


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 20000
    rng = random.Random(seed)
    base = json.loads(src.read_text(encoding="utf-8"))
    assert residual(base["u"], base["v"], base["w"]) == 0
    rank0 = len(base["u"])
    print(f"start rank={rank0} support={support(base['u'], base['v'], base['w'])} rounds={rounds}", flush=True)

    best_exact = None
    best_rank = rank0
    best_res = 10**9
    best_near = None
    hits_exact = 0
    t0 = time.time()

    # Try each single deletion, then local repair
    for drop_t in range(rank0):
        cur = drop_product(base, drop_t)
        res = residual(cur["u"], cur["v"], cur["w"])
        if res < best_res:
            best_res, best_near = res, deepcopy(cur)
        if res == 0:
            hits_exact += 1
            best_exact = cur
            best_rank = len(cur["u"])
            print(f"HIT drop t={drop_t} rank={best_rank}", flush=True)
            break
        # local repair budget per deletion
        budget = max(200, rounds // rank0)
        for step in range(budget):
            cand = flip_entry(cur, rng)
            new_res = residual(cand["u"], cand["v"], cand["w"])
            if new_res < res or (new_res == res and rng.random() < 0.05) or rng.random() < 0.002:
                cur, res = cand, new_res
                if res < best_res:
                    best_res, best_near = res, deepcopy(cur)
                if res == 0:
                    hits_exact += 1
                    best_exact = deepcopy(cur)
                    best_rank = len(cur["u"])
                    print(
                        f"HIT repaired drop={drop_t} step={step} rank={best_rank} "
                        f"support={support(cur['u'], cur['v'], cur['w'])}",
                        flush=True,
                    )
                    break
        if best_exact is not None:
            break
        if (drop_t + 1) % 5 == 0:
            print(
                f"status drops={drop_t+1}/{rank0} best_res={best_res} "
                f"hits={hits_exact} elapsed_s={time.time()-t0:.1f}",
                flush=True,
            )

    # Extra free search: random drop 1–2 products then repair
    if best_exact is None:
        for r in range(rounds):
            cur = deepcopy(base)
            k = 1 if rng.random() < 0.7 else 2
            idxs = sorted(rng.sample(range(len(cur["u"])), k), reverse=True)
            for t in idxs:
                cur = drop_product(cur, t)
            res = residual(cur["u"], cur["v"], cur["w"])
            for _ in range(300):
                cand = flip_entry(cur, rng)
                new_res = residual(cand["u"], cand["v"], cand["w"])
                if new_res <= res or rng.random() < 0.01:
                    cur, res = cand, new_res
                if res == 0:
                    best_exact = deepcopy(cur)
                    best_rank = len(cur["u"])
                    hits_exact += 1
                    print(f"HIT free r={r} rank={best_rank}", flush=True)
                    break
            if best_exact is not None:
                break
            if res < best_res:
                best_res, best_near = res, deepcopy(cur)
            if (r + 1) % 2000 == 0:
                print(
                    f"status free r={r+1} best_res={best_res} hits={hits_exact} "
                    f"elapsed_s={time.time()-t0:.1f}",
                    flush=True,
                )

    out.mkdir(parents=True, exist_ok=True)
    # Only persist exact Brent-ok decompositions as solution.json (avoid false rank progress)
    if best_exact is not None:
        final = best_exact
    else:
        final = base
    (out / "solution.json").write_text(
        json.dumps(final, separators=(",", ":")), encoding="utf-8"
    )
    if best_near is not None and best_exact is None:
        (out / "near_miss.json").write_text(
            json.dumps(best_near, separators=(",", ":")), encoding="utf-8"
        )
    cert = {
        "src": str(src),
        "start_rank": rank0,
        "best_rank": len(final["u"]) if best_exact is not None else rank0,
        "residual": residual(final["u"], final["v"], final["w"]),
        "support": support(final["u"], final["v"], final["w"]),
        "exact": best_exact is not None,
        "hits_exact": hits_exact,
        "best_near_residual": best_res if best_res < 10**9 else None,
        "near_rank": len(best_near["u"]) if best_near is not None else None,
    }
    (out / "rank_certificate.json").write_text(json.dumps(cert, indent=2), encoding="utf-8")
    print(f"done {cert}", flush=True)
    return 0 if best_exact is not None and len(best_exact["u"]) < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
