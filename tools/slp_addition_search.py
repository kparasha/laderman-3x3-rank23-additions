#!/usr/bin/env python3
"""Certified SLP addition search from Sun's rank-23 scheme.

Objective: minimize total SLP additions = cost(U)+cost(V)+cost(W)
subject to rank=23 and Brent identities = 0.

Cost model (Sun/Perminov): each intermediate is one addition;
each final form with k signed refs costs max(k-1, 0) additions.
"""

from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from pathlib import Path

# --- Sun SIDES (verify.py) -------------------------------------------------
SIDES0 = {
    "U": {
        "base_dim": 9,
        "inter": [
            (6, -1, 7), (4, -1, 9), (1, -1, 10), (11, -1, 6), (12, -1, 8),
            (1, -1, 13), (0, -1, 11), (13, 1, 2), (15, -1, 3), (17, 1, 5),
            (18, -1, 2), (0, -1, 1), (20, -1, 18),
        ],
        "final": [
            [(14, 1)], [(21, 1)], [(5, 1)], [(16, 1)], [(13, 1)], [(4, 1)],
            [(8, 1)], [(10, -1)], [(4, 1)], [(11, 1)], [(12, -1)], [(8, 1)],
            [(15, 1)], [(2, 1)], [(1, 1)], [(6, 1)], [(17, 1)], [(0, 1)],
            [(5, 1)], [(3, 1)], [(19, -1)], [(9, 1)], [(18, 1)],
        ],
    },
    "V": {
        "base_dim": 9,
        "inter": [
            (2, 1, 5), (3, -1, 5), (1, 1, 4), (8, -1, 9), (0, -1, 11),
            (2, -1, 13), (4, -1, 14), (7, -1, 15), (2, -1, 16), (8, 1, 16),
            (10, -1, 14), (8, 1, 19), (6, -1, 20),
        ],
        "final": [
            [(19, -1)], [(15, -1)], [(18, 1)], [(8, 1)], [(20, -1)], [(5, 1)],
            [(7, 1)], [(14, 1)], [(3, 1)], [(13, 1)], [(12, -1)], [(21, 1)],
            [(2, 1)], [(6, 1)], [(3, 1)], [(11, 1)], [(17, 1)], [(0, 1)],
            [(6, 1)], [(0, 1)], [(7, 1)], [(4, 1)], [(16, -1)],
        ],
    },
    "W": {
        "base_dim": 23,
        "inter": [
            (4, 1, 9), (12, 1, 22), (14, 1, 23), (0, 1, 7), (1, -1, 7),
            (10, 1, 25), (16, -1, 24),
        ],
        "final": [
            [(13, 1), (14, 1), (17, 1)],
            [(9, -1), (17, 1), (20, 1), (24, -1), (27, 1)],
            [(3, 1), (12, 1), (25, 1), (26, 1)],
            [(8, 1), (18, 1), (19, 1)],
            [(19, 1), (21, 1), (27, 1), (29, 1)],
            [(2, 1), (5, 1), (29, -1)],
            [(8, -1), (11, 1), (15, 1), (28, 1)],
            [(6, 1), (15, 1), (21, -1)],
            [(5, -1), (26, 1), (28, 1)],
        ],
    },
}


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
    return out, vs


def cost(side) -> int:
    extra = sum(max(sum(abs(c) for _, c in f) - 1, 0) for f in side["final"])
    return len(side["inter"]) + extra


def total_cost(sides) -> int:
    return cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"])


def sun_uvw_hill(sides):
    """UVW under hill conventions (W column-major)."""
    U = [list(r) for r in expand(sides["U"])[0]]
    V = [list(r) for r in expand(sides["V"])[0]]
    W_cols = expand(sides["W"])[0]  # 9 vectors length 23, row-major C
    W = []
    for r in range(23):
        row = [0] * 9
        for i in range(3):
            for j in range(3):
                sun_idx = 3 * i + j
                hill_idx = 3 * j + i
                row[hill_idx] = W_cols[sun_idx][r]
        W.append(row)
    return U, V, W


def brent_ok(u, v, w) -> bool:
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(len(u)))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                expected = int(inner == b_inner and c == 3 * col + row)
                if s != expected:
                    return False
    return True


def canon(v):
    t = tuple(v)
    neg = tuple(-x for x in t)
    return min(t, neg), (t <= neg)


def build_slp_greedy(targets, seed=0, max_extra=40):
    """Rebuild an SLP for target vectors from ±basis using greedy intersections.

    Returns (side_dict, cost) or None.
    """
    rng = random.Random(seed)
    if not targets:
        return {"base_dim": 0, "inter": [], "final": []}, 0
    dim = len(targets[0])
    basis = [tuple(1 if i == j else 0 for j in range(dim)) for i in range(dim)]
    # Normalize targets to canon for building, remember signs for finals
    wanted = []
    for t in targets:
        c, pos = canon(t)
        wanted.append((c, 1 if pos else -1, tuple(t)))

    unique_needed = []
    for c, _, _ in wanted:
        if c not in unique_needed and c not in {canon(b)[0] for b in basis}:
            unique_needed.append(c)

    vs = list(basis)
    inter = []
    remaining = set(unique_needed)

    def available_canons():
        return {canon(v)[0]: i for i, v in enumerate(vs)}

    while remaining and len(inter) < max_extra + len(unique_needed):
        avail = available_canons()
        best = None
        best_score = -1
        # Try all pairs
        n = len(vs)
        order_i = list(range(n))
        order_j = list(range(n))
        rng.shuffle(order_i)
        rng.shuffle(order_j)
        for i in order_i:
            for j in order_j:
                if i == j:
                    continue
                for s in (1, -1):
                    g = tuple(vs[i][k] + s * vs[j][k] for k in range(dim))
                    if all(x == 0 for x in g):
                        continue
                    cg, _ = canon(g)
                    if cg in avail:
                        continue
                    # score: hits remaining + helps remaining
                    score = 0.0
                    if cg in remaining:
                        score += 100
                    # how many remaining are ±(cg ± existing)
                    for t in remaining:
                        for idx2, v2 in enumerate(vs):
                            for s2 in (1, -1):
                                h = tuple(cg[k] + s2 * v2[k] for k in range(dim))
                                if canon(h)[0] == t:
                                    score += 1
                                    break
                    score += rng.random() * 0.01
                    if score > best_score:
                        best_score = score
                        best = (i, s, j, g, cg)
        if best is None:
            break
        i, s, j, g, cg = best
        vs.append(g)
        inter.append((i, s, j))
        remaining.discard(cg)

    # Build finals: express each original target as signed combo of vs
    avail_list = list(vs)
    finals = []
    for original in targets:
        # Prefer single-ref
        found = None
        for idx, v in enumerate(avail_list):
            if v == original:
                found = [(idx, 1)]
                break
            if tuple(-x for x in v) == original:
                found = [(idx, -1)]
                break
        if found is None:
            # Fall back: sum of signed basis (always works for integer vectors)
            terms = []
            for i, c in enumerate(original):
                if c != 0:
                    terms.append((i, c))
            found = terms
        finals.append(found)

    side = {"base_dim": dim, "inter": inter, "final": finals}
    # Verify expansion matches
    out, _ = expand(side)
    if [tuple(x) for x in out] != [tuple(t) for t in targets]:
        return None
    return side, cost(side)


def rebuild_sides_from_uvw(u, v, w_hill, seed=0):
    """Rebuild U,V,W SLPs from factor matrices. W stored as Sun row-major columns."""
    # Convert hill W rows -> Sun W columns (row-major C)
    w_cols = []
    for i in range(3):
        for j in range(3):
            sun_idx = 3 * i + j
            hill_idx = 3 * j + i
            col = tuple(w_hill[r][hill_idx] for r in range(23))
            w_cols.append(col)

    sides = {}
    for name, targets, s_off in (
        ("U", [tuple(r) for r in u], seed),
        ("V", [tuple(r) for r in v], seed + 17),
        ("W", w_cols, seed + 39),
    ):
        built = build_slp_greedy(targets, seed=s_off)
        if built is None:
            return None
        sides[name] = built[0]
    return sides


def sign_flip_scheme(u, v, w, signs):
    """Scale product t by signs[t] in {±1}: U*=s, V*=s keeps M; use U*=s, W*=s."""
    u2, v2, w2 = deepcopy(u), deepcopy(v), deepcopy(w)
    for t, s in enumerate(signs):
        if s == 1:
            continue
        u2[t] = [-x for x in u2[t]]
        w2[t] = [-x for x in w2[t]]
    return u2, v2, w2


def permute_products(u, v, w, perm):
    return (
        [u[i] for i in perm],
        [v[i] for i in perm],
        [w[i] for i in perm],
    )


def search(rounds=200, seed=0):
    rng = random.Random(seed)
    base_u, base_v, base_w = sun_uvw_hill(SIDES0)
    assert brent_ok(base_u, base_v, base_w)
    base_sides = SIDES0
    best_sides = deepcopy(base_sides)
    best_c = total_cost(best_sides)
    best_uvw = (base_u, base_v, base_w)
    print(f"Sun certified baseline cost={best_c} "
          f"(U={cost(SIDES0['U'])} V={cost(SIDES0['V'])} W={cost(SIDES0['W'])})")

    # Phase A: rebuild CSE from Sun UVW with many seeds (same factors, better schedule)
    for r in range(rounds):
        s = seed + r
        sides = rebuild_sides_from_uvw(base_u, base_v, base_w, seed=s)
        if sides is None:
            continue
        # Prefer keeping Sun's known-good sides if rebuild is worse; still check
        u, v, w = sun_uvw_hill(sides)
        # Rebuild may produce equivalent UVW; verify Brent
        if not brent_ok(u, v, w):
            # If SLP expands to same targets it should match; skip bad
            continue
        c = total_cost(sides)
        if c < best_c:
            best_c = c
            best_sides = sides
            best_uvw = (u, v, w)
            print(f"rebuild seed={s}: cost -> {best_c} "
                  f"(U={cost(sides['U'])} V={cost(sides['V'])} W={cost(sides['W'])})")

    # Phase B: random product sign flips then rebuild CSE
    for r in range(rounds):
        signs = [rng.choice([-1, 1]) for _ in range(23)]
        u, v, w = sign_flip_scheme(base_u, base_v, base_w, signs)
        if not brent_ok(u, v, w):
            continue
        sides = rebuild_sides_from_uvw(u, v, w, seed=seed + 1000 + r)
        if sides is None:
            continue
        uu, vv, ww = sun_uvw_hill(sides)
        if not brent_ok(uu, vv, ww):
            continue
        c = total_cost(sides)
        if c < best_c:
            best_c = c
            best_sides = sides
            best_uvw = (uu, vv, ww)
            print(f"signflip r={r}: cost -> {best_c} "
                  f"(U={cost(sides['U'])} V={cost(sides['V'])} W={cost(sides['W'])})")

    # Phase C: random product permutations then rebuild
    for r in range(rounds // 2):
        perm = list(range(23))
        rng.shuffle(perm)
        u, v, w = permute_products(base_u, base_v, base_w, perm)
        assert brent_ok(u, v, w)
        sides = rebuild_sides_from_uvw(u, v, w, seed=seed + 2000 + r)
        if sides is None:
            continue
        uu, vv, ww = sun_uvw_hill(sides)
        if not brent_ok(uu, vv, ww):
            continue
        c = total_cost(sides)
        if c < best_c:
            best_c = c
            best_sides = sides
            best_uvw = (uu, vv, ww)
            print(f"perm r={r}: cost -> {best_c} "
                  f"(U={cost(sides['U'])} V={cost(sides['V'])} W={cost(sides['W'])})")

    return best_c, best_sides, best_uvw


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    best_c, best_sides, (u, v, w) = search(rounds=rounds, seed=seed)

    out_dir = Path("submissions/attempt015-sun-cse")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"u": u, "v": v, "w": w}
    (out_dir / "solution.json").write_text(
        json.dumps(payload, separators=(",", ":")), encoding="utf-8"
    )
    cert = {
        "objective": "minimize certified SLP additions @ rank 23, Brent=0",
        "baseline_sun_cost": 56,
        "certified_cost": best_c,
        "breakdown": {
            "U": cost(best_sides["U"]),
            "V": cost(best_sides["V"]),
            "W": cost(best_sides["W"]),
        },
        "improved": best_c < 56,
        "rank": 23,
        "brent_ok": brent_ok(u, v, w),
        "support": sum(x != 0 for M in (u, v, w) for row in M for x in row),
    }
    (out_dir / "slp_certificate.json").write_text(
        json.dumps(cert, indent=2), encoding="utf-8"
    )
    # Keep sides for reproducibility
    (out_dir / "sides.json").write_text(
        json.dumps(best_sides, indent=2), encoding="utf-8"
    )
    print(json.dumps(cert, indent=2))
    return 0 if cert["brent_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
