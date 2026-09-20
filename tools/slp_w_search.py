#!/usr/bin/env python3
"""Minimize certified SLP additions for Sun's rank-23 scheme (W-focused).

Sun claims U≥13, V≥13 optimality on this factorization. Beating 56 therefore
requires W < 30 (or a different factorization). This tool:

1. Keeps Sun U/V SLPs fixed (13+13).
2. Rebuilds W CSE with many greedy seeds / random construction orders.
3. Also tries product sign-flips (U[t],W[t] *= ±1) then rebuilds W only.
4. Certifies: expand SLP → Brent OK, cost = len(inter)+final extras.

Usage:
  python3 -u tools/slp_w_search.py [seed] [rounds]
"""

from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from pathlib import Path

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


def cost(side: dict) -> int:
    extra = sum(max(sum(abs(c) for _, c in f) - 1, 0) for f in side["final"])
    return len(side["inter"]) + extra


def sun_uvw_hill(sides):
    U = [list(r) for r in expand(sides["U"])[0]]
    V = [list(r) for r in expand(sides["V"])[0]]
    W_cols = expand(sides["W"])[0]
    W = []
    for r in range(23):
        row = [0] * 9
        for i in range(3):
            for j in range(3):
                row[3 * j + i] = W_cols[3 * i + j][r]
        W.append(row)
    return U, V, W


def brent_ok(u, v, w) -> bool:
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(23))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                if s != int(inner == b_inner and c == 3 * col + row):
                    return False
    return True


def express(target, vs):
    """Express target as list of (idx, coeff) over current vectors, preferring sparse."""
    # Exact single match
    for i, v in enumerate(vs):
        if v == target:
            return [(i, 1)]
        if tuple(-x for x in v) == target:
            return [(i, -1)]
    # Two-term: target = ±vs[a] ± vs[b]
    n = len(vs)
    dim = len(target)
    for i in range(n):
        for j in range(i):
            for sa in (1, -1):
                for sb in (1, -1):
                    g = tuple(sa * vs[i][k] + sb * vs[j][k] for k in range(dim))
                    if g == target:
                        return [(i, sa), (j, sb)]
    # Three-term search (bounded)
    for i in range(n):
        for j in range(i):
            for k in range(j):
                for sa in (1, -1):
                    for sb in (1, -1):
                        for sc in (1, -1):
                            g = tuple(
                                sa * vs[i][t] + sb * vs[j][t] + sc * vs[k][t]
                                for t in range(dim)
                            )
                            if g == target:
                                return [(i, sa), (j, sb), (k, sc)]
    # Fallback: basis expansion
    return [(i, c) for i, c in enumerate(target) if c != 0]


def build_w_slp(targets, rng, max_inter=20):
    """Greedy intersection CSE for W columns (length-23 vectors)."""
    dim = 23
    vs = [tuple(1 if i == j else 0 for j in range(dim)) for i in range(dim)]
    inter = []

    # Targets that are not ±basis need work
    def is_unit(t):
        return sum(abs(x) for x in t) == 1

    pending = [t for t in targets if not is_unit(t)]
    # Unique up to sign
    uniq = []
    seen = set()
    for t in pending:
        key = min(t, tuple(-x for x in t))
        if key not in seen:
            seen.add(key)
            uniq.append(key)
    pending_set = set(uniq)

    while pending_set and len(inter) < max_inter:
        best = None
        best_score = -1.0
        n = len(vs)
        # Sample pairs if large
        pairs = [(i, j, s) for i in range(n) for j in range(i) for s in (1, -1)]
        if len(pairs) > 2000:
            pairs = rng.sample(pairs, 2000)
        for i, j, s in pairs:
            g = tuple(vs[i][k] + s * vs[j][k] for k in range(dim))
            if all(x == 0 for x in g):
                continue
            cg = min(g, tuple(-x for x in g))
            # already have?
            if any(min(v, tuple(-x for x in v)) == cg for v in vs):
                continue
            score = 0.0
            if cg in pending_set:
                score += 50
            # usefulness: how many pending are ±(g ± existing)
            for t in pending_set:
                for idx2 in range(n):
                    for s2 in (1, -1):
                        h = tuple(g[k] + s2 * vs[idx2][k] for k in range(dim))
                        if min(h, tuple(-x for x in h)) == t:
                            score += 1
                            break
            score += rng.random() * 0.01
            if score > best_score:
                best_score = score
                best = (i, s, j, g, cg)
        if best is None or best_score < 0.5:
            break
        i, s, j, g, cg = best
        vs.append(g)
        inter.append((i, s, j))
        pending_set.discard(cg)

    finals = [express(t, vs) for t in targets]
    side = {"base_dim": dim, "inter": inter, "final": finals}
    out, _ = expand(side)
    if out != list(targets):
        return None
    return side


def w_cols_from_hill(w_hill):
    cols = []
    for i in range(3):
        for j in range(3):
            cols.append(tuple(w_hill[r][3 * j + i] for r in range(23)))
    return cols


def signflip_uw(u, v, w, signs):
    u2 = deepcopy(u)
    w2 = deepcopy(w)
    for t, s in enumerate(signs):
        if s < 0:
            u2[t] = [-x for x in u2[t]]
            w2[t] = [-x for x in w2[t]]
    return u2, v, w2


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    rng = random.Random(seed)

    sides = deepcopy(SIDES0)
    u0, v0, w0 = sun_uvw_hill(sides)
    assert brent_ok(u0, v0, w0)
    best_total = cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"])
    best_sides = deepcopy(sides)
    best_uvw = (u0, v0, w0)
    print(
        f"baseline total={best_total} "
        f"U={cost(sides['U'])} V={cost(sides['V'])} W={cost(sides['W'])}",
        flush=True,
    )

    def consider(new_w_side, u, v, w, tag):
        nonlocal best_total, best_sides, best_uvw
        if new_w_side is None:
            return
        cW = cost(new_w_side)
        total = cost(SIDES0["U"]) + cost(SIDES0["V"]) + cW
        # Build full sides with Sun U/V + new W
        trial = {"U": SIDES0["U"], "V": SIDES0["V"], "W": new_w_side}
        # If U/V factors changed via signflip, need to rebuild U SLP or keep UVW directly
        # For certification we hills-eval UVW; SLP cost uses trial sides only when
        # expand(U),expand(V) match u,v. Signflip changes U rows → keep expanded UVW
        # and only trust W cost if U/V are still Sun's.
        uu, vv, ww = u, v, w
        if not brent_ok(uu, vv, ww):
            return
        # Recompute W cost against actual w columns from this UVW
        # (new_w_side already verified to expand to those columns)
        if total < best_total:
            best_total = total
            best_sides = trial
            best_uvw = (uu, vv, ww)
            print(
                f"{tag}: total -> {best_total} (W={cW})",
                flush=True,
            )

    # Phase 1: rebuild W CSE from Sun W columns
    cols0 = w_cols_from_hill(w0)
    for r in range(rounds):
        rng_r = random.Random(seed + r)
        side = build_w_slp(cols0, rng_r, max_inter=16)
        consider(side, u0, v0, w0, f"W-rebuild#{r}")

    # Phase 2: sign-flip products, keep V, flip U&W, rebuild W CSE
    # Also need U SLP cost: after flip, use naive U rebuild cost estimate via build on U rows
    for r in range(rounds):
        signs = [rng.choice([-1, 1]) for _ in range(23)]
        u, v, w = signflip_uw(u0, v0, w0, signs)
        if not brent_ok(u, v, w):
            continue
        cols = w_cols_from_hill(w)
        sideW = build_w_slp(cols, random.Random(seed + 10_000 + r), max_inter=16)
        if sideW is None:
            continue
        # U cost may change; rebuild U quickly with same builder on dim=9
        # Reuse W builder generalized: for dim=9 targets = u rows
        # For fairness vs Sun, compute U cost with a dim-9 version
        def build_generic(targets, dim, rng2, max_inter=20):
            vs = [tuple(1 if i == j else 0 for j in range(dim)) for i in range(dim)]
            inter = []
            pending = []
            seen = set()
            for t in targets:
                key = min(t, tuple(-x for x in t))
                if sum(abs(x) for x in t) == 1:
                    continue
                if key not in seen:
                    seen.add(key)
                    pending.append(key)
            pending_set = set(pending)
            while pending_set and len(inter) < max_inter:
                best = None
                best_score = -1.0
                n = len(vs)
                pairs = [(i, j, s) for i in range(n) for j in range(i) for s in (1, -1)]
                if len(pairs) > 1500:
                    pairs = rng2.sample(pairs, 1500)
                for i, j, s in pairs:
                    g = tuple(vs[i][k] + s * vs[j][k] for k in range(dim))
                    if all(x == 0 for x in g):
                        continue
                    cg = min(g, tuple(-x for x in g))
                    if any(min(v, tuple(-x for x in v)) == cg for v in vs):
                        continue
                    score = (50.0 if cg in pending_set else 0.0) + rng2.random() * 0.01
                    for t in pending_set:
                        for idx2 in range(min(n, 30)):
                            for s2 in (1, -1):
                                h = tuple(g[k] + s2 * vs[idx2][k] for k in range(dim))
                                if min(h, tuple(-x for x in h)) == t:
                                    score += 1
                                    break
                    if score > best_score:
                        best_score = score
                        best = (i, s, j, g, cg)
                if best is None or best_score < 0.5:
                    break
                i, s, j, g, cg = best
                vs.append(g)
                inter.append((i, s, j))
                pending_set.discard(cg)
            finals = [express(t, vs) for t in targets]
            side = {"base_dim": dim, "inter": inter, "final": finals}
            out, _ = expand(side)
            if out != list(targets):
                return None
            return side

        sideU = build_generic([tuple(r) for r in u], 9, random.Random(seed + 20_000 + r), 20)
        sideV = build_generic([tuple(r) for r in v], 9, random.Random(seed + 30_000 + r), 20)
        if sideU is None or sideV is None:
            continue
        total = cost(sideU) + cost(sideV) + cost(sideW)
        if total < best_total and brent_ok(u, v, w):
            best_total = total
            best_sides = {"U": sideU, "V": sideV, "W": sideW}
            best_uvw = (u, v, w)
            print(
                f"signflip#{r}: total -> {best_total} "
                f"(U={cost(sideU)} V={cost(sideV)} W={cost(sideW)})",
                flush=True,
            )

    u, v, w = best_uvw
    out = Path("submissions/attempt015-additions")
    out.mkdir(parents=True, exist_ok=True)
    (out / "solution.json").write_text(
        json.dumps({"u": u, "v": v, "w": w}, separators=(",", ":")), encoding="utf-8"
    )
    cert = {
        "objective": "min certified SLP additions | rank=23 | Brent=0",
        "baseline": 56,
        "certified_cost": best_total,
        "breakdown": {
            "U": cost(best_sides["U"]),
            "V": cost(best_sides["V"]),
            "W": cost(best_sides["W"]),
        },
        "improved": best_total < 56,
        "brent_ok": brent_ok(u, v, w),
        "rank": len(u),
        "support": sum(x != 0 for M in (u, v, w) for row in M for x in row),
    }
    (out / "slp_certificate.json").write_text(json.dumps(cert, indent=2), encoding="utf-8")
    (out / "sides.json").write_text(json.dumps(best_sides), encoding="utf-8")
    print(json.dumps(cert, indent=2), flush=True)
    return 0 if cert["brent_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
