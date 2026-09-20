#!/usr/bin/env python3
"""Greedy intersection CSE for ternary linear forms (Perminov-style).

Builds an SLP that computes a list of target vectors from the standard basis
using binary ± combinations. Unofficial addition count for climbing toward <56.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path


def canon(v):
    t = tuple(v)
    neg = tuple(-x for x in t)
    return min(t, neg)


def add(a, b, sa=1, sb=1):
    return tuple(sa * a[i] + sb * b[i] for i in range(len(a)))


def is_basis(v):
    return sum(abs(x) for x in v) == 1


def cse_cost(targets, seed=0, passes=3):
    """Return (cost, program) for computing all targets from basis via ± pairs."""
    rng = random.Random(seed)
    dim = len(targets[0])
    basis = [tuple(1 if i == j else 0 for j in range(dim)) for i in range(dim)]
    best = None
    for p in range(passes):
        remaining = [canon(t) for t in targets if not is_basis(canon(t))]
        # unique
        uniq = []
        for t in remaining:
            if t not in uniq:
                uniq.append(t)
        remaining = uniq
        vs = list(basis)
        inter = []
        # Greedy: while remaining, pick a pair of available vectors whose ± combo
        # hits the most remaining targets / useful intermediates
        while remaining:
            best_move = None
            best_score = -1
            # candidates: all pairs among vs
            for i in range(len(vs)):
                for j in range(i):
                    for sa, sb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                        g = add(vs[i], vs[j], sa, sb)
                        if all(x == 0 for x in g):
                            continue
                        cg = canon(g)
                        if cg in {canon(v) for v in vs}:
                            continue
                        # score: how many remaining equal cg, plus how many remaining
                        # become 1-step from cg
                        score = 0
                        if cg in remaining:
                            score += 10
                        for t in remaining:
                            # can we make t from cg and something in vs?
                            for k, vk in enumerate(vs):
                                for s1, s2 in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                                    if canon(add(cg, vk, s1, s2)) == t:
                                        score += 1
                                        break
                        # small noise
                        score += rng.random() * 0.01
                        if score > best_score:
                            best_score = score
                            best_move = (i, j, sa, sb, g, cg)
            if best_move is None:
                # fallback: synthesize each remaining as sum of its ±basis (no CSE)
                for t in list(remaining):
                    # count naive
                    pass
                break
            i, j, sa, sb, g, cg = best_move
            vs.append(g)
            inter.append((i, sa if sa == 1 else -1, j))  # store like Sun: (a,s,b) meaning vs[a]+s*vs[b]
            # Sun uses (a,s,b) with s in {±1}: vs.append(va + s*vb)
            # Fix encoding: a,s,b where result = vs[a] + s*vs[b]
            inter[-1] = (i, sb if True else 1, j)
            # Correct: g = sa*vs[i] + sb*vs[j]. Sun only allows vs[a]+s*vs[b].
            # Normalize so leading is +1 by swapping/signs.
            if sa == -1 and sb == -1:
                # g = -(vs[i]+vs[j]); store vs[i]+vs[j] then remember sign in final
                inter[-1] = (i, 1, j)
                g = add(vs[i], vs[j], 1, 1)
                vs[-1] = g
            elif sa == -1 and sb == 1:
                inter[-1] = (j, -1, i)  # vs[j] + (-1)*vs[i]
                g = add(vs[j], vs[i], 1, -1)
                vs[-1] = g
            elif sa == 1 and sb == -1:
                inter[-1] = (i, -1, j)
            else:
                inter[-1] = (i, 1, j)
            cg = canon(vs[-1])
            remaining = [t for t in remaining if t != cg]

        # Final cost: len(inter) + extras for finals that combine multiple vs
        # Map each target to a signed available vector or small combination
        finals = []
        cost_extra = 0
        available = list(vs)
        for t in targets:
            ct = canon(t)
            found = None
            for idx, v in enumerate(available):
                if canon(v) == ct:
                    # sign
                    sign = 1 if v == t or (tuple(-x for x in v) != t and v == t) else (
                        1 if v == t else -1
                    )
                    if v == t:
                        sign = 1
                    elif tuple(-x for x in v) == t:
                        sign = -1
                    else:
                        continue
                    found = [(idx, sign)]
                    break
            if found is None:
                # build from nonzero basis terms (naive)
                terms = []
                for i, c in enumerate(t):
                    if c == 0:
                        continue
                    # find basis vector i
                    terms.append((i, c))
                found = terms
                cost_extra += max(sum(abs(c) for _, c in terms) - 1, 0)
            else:
                cost_extra += max(sum(abs(c) for _, c in found) - 1, 0)
            finals.append(found)
        total = len(inter) + cost_extra
        if best is None or total < best[0]:
            best = (total, inter, finals)
    return best


def scheme_addition_estimate(path: Path, seed=0):
    data = json.loads(path.read_text(encoding="utf-8"))
    u, v, w = data["u"], data["v"], data["w"]
    # W as 9 vectors of length 23 (columns) for CSE of output side
    w_cols = [[w[r][c] for r in range(len(w))] for c in range(9)]
    cu, _, _ = cse_cost([tuple(r) for r in u], seed=seed)
    cv, _, _ = cse_cost([tuple(r) for r in v], seed=seed + 1)
    cw, _, _ = cse_cost([tuple(r) for r in w_cols], seed=seed + 2)
    return {"U": cu, "V": cv, "W": cw, "total": cu + cv + cw}


def main():
    src = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    est = scheme_addition_estimate(src, seed=seed)
    print(json.dumps(est, indent=2))
    print("unofficial CSE estimate; compare to Sun certified 56")


if __name__ == "__main__":
    main()
