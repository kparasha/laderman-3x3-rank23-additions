#!/usr/bin/env python3
"""Exhaustive single-zero and random double-flip search for lower support."""

from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from pathlib import Path


def brent_ok(u, v, w) -> bool:
    rank = len(u)
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(rank))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                expected = int(inner == b_inner and c == 3 * col + row)
                if s != expected:
                    return False
    return True


def support(u, v, w) -> int:
    return sum(x != 0 for M in (u, v, w) for row in M for x in row)


def mats(data):
    return data["u"], data["v"], data["w"]


def positions(u, v, w):
    out = []
    for name, M in (("u", u), ("v", v), ("w", w)):
        for t, row in enumerate(M):
            for i, x in enumerate(row):
                if x != 0:
                    out.append((name, t, i))
    return out


def get(data, name, t, i):
    return data[name][t][i]


def setv(data, name, t, i, val):
    data[name][t][i] = val


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    double_rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 20000
    rng = random.Random(seed)
    best = json.loads(src.read_text(encoding="utf-8"))
    assert brent_ok(*mats(best))
    best_s = support(*mats(best))
    print(f"start {best_s}")

    # Phase 1: try zeroing each nonzero once
    cur = deepcopy(best)
    changed = True
    while changed:
        changed = False
        for name, t, i in positions(*mats(cur)):
            old = get(cur, name, t, i)
            setv(cur, name, t, i, 0)
            if brent_ok(*mats(cur)):
                s = support(*mats(cur))
                if s < best_s:
                    best = deepcopy(cur)
                    best_s = s
                    changed = True
                    print(f"zero {name}[{t}][{i}] -> {best_s}")
                    break
            setv(cur, name, t, i, old)
        cur = deepcopy(best)

    # Phase 2: random double edits (set to ternary)
    cur = deepcopy(best)
    for r in range(double_rounds):
        pos = positions(*mats(cur))
        if len(pos) < 2:
            break
        (n1, t1, i1), (n2, t2, i2) = rng.sample(pos, 2)
        o1, o2 = get(cur, n1, t1, i1), get(cur, n2, t2, i2)
        nval1 = rng.choice([0, 1, -1])
        nval2 = rng.choice([0, 1, -1])
        if (nval1, nval2) == (o1, o2):
            continue
        setv(cur, n1, t1, i1, nval1)
        setv(cur, n2, t2, i2, nval2)
        if brent_ok(*mats(cur)):
            s = support(*mats(cur))
            if s <= best_s:
                if s < best_s:
                    print(f"double round {r}: {best_s} -> {s}")
                best = deepcopy(cur)
                best_s = s
            # keep even if equal support (diversify)
        else:
            setv(cur, n1, t1, i1, o1)
            setv(cur, n2, t2, i2, o2)
            cur = deepcopy(best)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(best, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} support={best_s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
