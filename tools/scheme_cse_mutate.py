#!/usr/bin/env python3
"""Additions search on an arbitrary UVW scheme via product sign-flips + multi-seed CSE.

Different basin than Sun-only tools: feed Stapleton / Perminov / Laderman, aim total < 56.

  python3 -u tools/scheme_cse_mutate.py submissions/stapleton60/solution.json \\
      submissions/director-add-stapleton-cse 91 3000
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path


def brent_ok(u, v, w) -> bool:
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(len(u)))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                if s != int(inner == b_inner and c == 3 * col + row):
                    return False
    return True


def expand(side):
    n = side["base_dim"]
    vs = [tuple(1 if i == j else 0 for j in range(n)) for i in range(n)]
    for a, s, b in side["inter"]:
        va, vb = vs[a], vs[b]
        vs.append(tuple(va[i] + s * vb[i] for i in range(n)))
    out = []
    for f in side["final"]:
        acc = [0] * n
        for idx, c in f:
            v = vs[idx]
            for i in range(n):
                acc[i] += c * v[i]
        out.append(tuple(acc))
    return out


def cost(side) -> int:
    extra = sum(max(sum(abs(c) for _, c in f) - 1, 0) for f in side["final"])
    return len(side["inter"]) + extra


def greedy_cse(targets, rng, max_extract=50):
    dim = len(targets[0])
    exprs = []
    for t in targets:
        terms = [(i, t[i]) for i in range(dim) if t[i] != 0]
        if any(abs(c) != 1 for _, c in terms):
            return None
        exprs.append(terms)
    inter = []

    def pair_key(i, si, j, sj):
        return (i, si, j, sj) if (i, si) <= (j, sj) else (j, sj, i, si)

    for _ in range(max_extract):
        counts = Counter()
        locations = {}
        for ei, expr in enumerate(exprs):
            if len(expr) < 2:
                continue
            seen_local = set()
            for (a, sa), (b, sb) in combinations(expr, 2):
                key = pair_key(a, sa, b, sb)
                if key in seen_local:
                    continue
                seen_local.add(key)
                counts[key] += 1
                locations.setdefault(key, []).append(ei)
        cands = [k for k, c in counts.items() if c >= 2]
        if not cands:
            break
        cands.sort(key=lambda k: (-counts[k], rng.random()))
        top = counts[cands[0]]
        key = rng.choice([k for k in cands if counts[k] == top])
        a, sa, b, sb = key
        new_idx = dim + len(inter)
        inter.append((a, sb * sa, b))
        for ei in locations[key]:
            expr = exprs[ei]
            new_expr, ra, rb = [], False, False
            for n, s in expr:
                if not ra and n == a and s == sa:
                    ra = True
                    continue
                if not rb and n == b and s == sb:
                    rb = True
                    continue
                new_expr.append((n, s))
            if ra and rb:
                new_expr.append((new_idx, sa))
                exprs[ei] = new_expr
    side = {"base_dim": dim, "inter": inter, "final": [list(e) for e in exprs]}
    if expand(side) != list(targets):
        return None
    return side


def w_cols(w):
    return [tuple(w[r][3 * j + i] for r in range(len(w))) for i in range(3) for j in range(3)]


def score(u, v, w, n_seeds, seed):
    best = None
    best_sides = None
    for s in range(n_seeds):
        rng = random.Random(seed * 1009 + s)
        su = greedy_cse([tuple(r) for r in u], rng)
        sv = greedy_cse([tuple(r) for r in v], random.Random(seed * 1009 + s + 17))
        sw = greedy_cse(w_cols(w), random.Random(seed * 1009 + s + 101))
        if None in (su, sv, sw):
            continue
        tot = cost(su) + cost(sv) + cost(sw)
        if best is None or tot < best:
            best = tot
            best_sides = {"U": su, "V": sv, "W": sw}
    return best, best_sides


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    trials = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
    n_seeds = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    data = json.loads(src.read_text(encoding="utf-8"))
    u0, v0, w0 = data["u"], data["v"], data["w"]
    assert brent_ok(u0, v0, w0)
    base, base_sides = score(u0, v0, w0, max(n_seeds, 4), seed)
    if base is None:
        print("baseline CSE failed")
        return 2
    best = base
    best_uvw = (u0, v0, w0)
    best_sides = base_sides
    hist = Counter({base: 1})
    improvements = 0
    t0 = time.time()
    print(
        f"start src={src} rank={len(u0)} greedy_cse={base} trials={trials} seed={seed}",
        flush=True,
    )
    for t in range(1, trials + 1):
        rng = random.Random(seed * 1_000_003 + t)
        u = [r[:] for r in u0]
        v = [r[:] for r in v0]
        w = [r[:] for r in w0]
        for i in range(len(u)):
            if rng.random() < 0.25:
                u[i] = [-x for x in u[i]]
                w[i] = [-x for x in w[i]]
            if rng.random() < 0.25:
                v[i] = [-x for x in v[i]]
                w[i] = [-x for x in w[i]]
        if not brent_ok(u, v, w):
            continue
        tot, sides = score(u, v, w, n_seeds, seed + t)
        if sides is None:
            continue
        hist[tot] += 1
        if tot < best:
            improvements += 1
            print(
                f"IMPROVED t={t} {best} -> {tot} "
                f"(U={cost(sides['U'])} V={cost(sides['V'])} W={cost(sides['W'])})",
                flush=True,
            )
            best, best_uvw, best_sides = tot, (u, v, w), sides
        if t % max(200, trials // 10) == 0:
            le56 = sum(v for k, v in hist.items() if k <= 56)
            print(
                f"status t={t} best={best} scored={sum(hist.values())} "
                f"improvements={improvements} le56={le56} "
                f"hist={dict(sorted(hist.items())[:8])} elapsed_s={time.time()-t0:.1f}",
                flush=True,
            )
    out.mkdir(parents=True, exist_ok=True)
    u, v, w = best_uvw
    (out / "solution.json").write_text(
        json.dumps({"u": u, "v": v, "w": w}, separators=(",", ":")), encoding="utf-8"
    )
    (out / "sides.json").write_text(json.dumps(best_sides, indent=2), encoding="utf-8")
    cert = {
        "src": str(src),
        "greedy_baseline": base,
        "certified_cost": best,
        "breakdown": {
            "U": cost(best_sides["U"]),
            "V": cost(best_sides["V"]),
            "W": cost(best_sides["W"]),
        },
        "improved": best < 56,
        "beat_baseline": best < base,
        "brent_ok": brent_ok(u, v, w),
        "rank": len(u),
        "support": sum(x != 0 for M in (u, v, w) for row in M for x in row),
        "improvements": improvements,
        "hist": {str(k): v for k, v in sorted(hist.items())},
    }
    (out / "slp_certificate.json").write_text(json.dumps(cert, indent=2), encoding="utf-8")
    print(
        f"done best={best} baseline={base} improvements={improvements} "
        f"le56={sum(v for k,v in hist.items() if k<=56)} wrote {out}",
        flush=True,
    )
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
