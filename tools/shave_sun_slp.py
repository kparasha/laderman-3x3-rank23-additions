#!/usr/bin/env python3
"""Try to shave additions from Sun's certified SLP by alternate intermediate choices."""

from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from pathlib import Path

# Sun SIDES (from verify.py)
SIDES0 = {
    "U": {
        "base_dim": 9,
        "inter": [
            (6, -1, 7),
            (4, -1, 9),
            (1, -1, 10),
            (11, -1, 6),
            (12, -1, 8),
            (1, -1, 13),
            (0, -1, 11),
            (13, 1, 2),
            (15, -1, 3),
            (17, 1, 5),
            (18, -1, 2),
            (0, -1, 1),
            (20, -1, 18),
        ],
        "final": [
            [(14, 1)],
            [(21, 1)],
            [(5, 1)],
            [(16, 1)],
            [(13, 1)],
            [(4, 1)],
            [(8, 1)],
            [(10, -1)],
            [(4, 1)],
            [(11, 1)],
            [(12, -1)],
            [(8, 1)],
            [(15, 1)],
            [(2, 1)],
            [(1, 1)],
            [(6, 1)],
            [(17, 1)],
            [(0, 1)],
            [(5, 1)],
            [(3, 1)],
            [(19, -1)],
            [(9, 1)],
            [(18, 1)],
        ],
    },
    "V": {
        "base_dim": 9,
        "inter": [
            (2, 1, 5),
            (3, -1, 5),
            (1, 1, 4),
            (8, -1, 9),
            (0, -1, 11),
            (2, -1, 13),
            (4, -1, 14),
            (7, -1, 15),
            (2, -1, 16),
            (8, 1, 16),
            (10, -1, 14),
            (8, 1, 19),
            (6, -1, 20),
        ],
        "final": [
            [(19, -1)],
            [(15, -1)],
            [(18, 1)],
            [(8, 1)],
            [(20, -1)],
            [(5, 1)],
            [(7, 1)],
            [(14, 1)],
            [(3, 1)],
            [(13, 1)],
            [(12, -1)],
            [(21, 1)],
            [(2, 1)],
            [(6, 1)],
            [(3, 1)],
            [(11, 1)],
            [(17, 1)],
            [(0, 1)],
            [(6, 1)],
            [(0, 1)],
            [(7, 1)],
            [(4, 1)],
            [(16, -1)],
        ],
    },
    "W": {
        "base_dim": 23,
        "inter": [
            (4, 1, 9),
            (12, 1, 22),
            (14, 1, 23),
            (0, 1, 7),
            (1, -1, 7),
            (10, 1, 25),
            (16, -1, 24),
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


def cost(side):
    extra = sum(max(sum(abs(c) for _, c in f) - 1, 0) for f in side["final"])
    return len(side["inter"]) + extra


def sun_uvw(sides):
    U = expand(sides["U"])[0]
    V = expand(sides["V"])[0]
    W_cols = expand(sides["W"])[0]
    RANK = 23
    W = []
    for r in range(RANK):
        row = [0] * 9
        for i in range(3):
            for j in range(3):
                sun_idx = 3 * i + j
                hill_idx = 3 * j + i
                row[hill_idx] = W_cols[sun_idx][r]
        W.append(row)
    return [list(r) for r in U], [list(r) for r in V], W


def brent_ok(u, v, w):
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(23))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                expected = int(inner == b_inner and c == 3 * col + row)
                if s != expected:
                    return False
    return True


def mutate_w(sides, rng):
    """Try adding one random intermediate on W and rewriting one final to use it."""
    s = deepcopy(sides)
    side = s["W"]
    n_vs = side["base_dim"] + len(side["inter"])
    if n_vs < 2:
        return sides
    a = rng.randrange(n_vs)
    b = rng.randrange(n_vs)
    if a == b:
        return sides
    sign = rng.choice([1, -1])
    side["inter"].append((a, sign, b))
    new_idx = n_vs  # index of new vector
    # rewrite a random multi-term final to maybe use new_idx
    fi = rng.randrange(len(side["final"]))
    f = side["final"][fi]
    if len(f) < 2:
        return sides
    # replace two terms with reference to new if they match - skip complex; just try shorter random final
    if rng.random() < 0.5 and len(f) >= 2:
        # drop one term randomly (may break)
        drop = rng.randrange(len(f))
        side["final"][fi] = [t for k, t in enumerate(f) if k != drop]
        side["final"][fi].append((new_idx, rng.choice([1, -1])))
    return s


def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    sides = deepcopy(SIDES0)
    u, v, w = sun_uvw(sides)
    assert brent_ok(u, v, w)
    best = deepcopy(sides)
    best_cost = cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"])
    print(f"start cost {best_cost} ({cost(sides['U'])}/{cost(sides['V'])}/{cost(sides['W'])})")
    improvements = 0
    for r in range(rounds):
        cand = mutate_w(sides, rng)
        try:
            u, v, w = sun_uvw(cand)
        except Exception:
            continue
        if not brent_ok(u, v, w):
            continue
        c = cost(cand["U"]) + cost(cand["V"]) + cost(cand["W"])
        if c < best_cost:
            best_cost = c
            best = deepcopy(cand)
            sides = cand
            improvements += 1
            print(f"round {r}: cost -> {best_cost}")
        elif c == best_cost and rng.random() < 0.05:
            sides = cand
    print(f"best_cost={best_cost} improvements={improvements}")
    u, v, w = sun_uvw(best)
    out = Path("submissions/attempt010-sun-slp/solution.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"u": u, "v": v, "w": w}, separators=(",", ":")), encoding="utf-8")
    Path("submissions/attempt010-sun-slp/slp_cost.json").write_text(
        json.dumps(
            {
                "U": cost(best["U"]),
                "V": cost(best["V"]),
                "W": cost(best["W"]),
                "total": best_cost,
                "official_adds_unofficial": best_cost,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
