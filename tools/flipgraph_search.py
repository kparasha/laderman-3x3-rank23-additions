#!/usr/bin/env python3
"""Flip-graph style search: start from schoolbook rank 27, flip toward rank 23, track support."""

from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from pathlib import Path


def schoolbook():
    u, v, w = [], [], []
    for row in range(3):
        for inner in range(3):
            for column in range(3):
                left, right, output = [0] * 9, [0] * 9, [0] * 9
                left[3 * row + inner] = 1
                right[3 * inner + column] = 1
                output[3 * column + row] = 1
                u.append(left)
                v.append(right)
                w.append(output)
    return {"u": u, "v": v, "w": w}


def brent_residual(u, v, w):
    bad = 0
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(len(u)))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                expected = int(inner == b_inner and c == 3 * col + row)
                if s != expected:
                    bad += 1
    return bad


def support(data):
    return sum(x != 0 for M in (data["u"], data["v"], data["w"]) for row in M for x in row)


def is_zero_term(data, t):
    return (
        all(x == 0 for x in data["u"][t])
        or all(x == 0 for x in data["v"][t])
        or all(x == 0 for x in data["w"][t])
    )


def compact_rank(data):
    """Drop fully-zero product terms."""
    keep = [t for t in range(len(data["u"])) if not is_zero_term(data, t)]
    return {
        "u": [data["u"][t] for t in keep],
        "v": [data["v"][t] for t in keep],
        "w": [data["w"][t] for t in keep],
    }


def flip(data, rng):
    """Random ternary flip of one coefficient."""
    d = deepcopy(data)
    name = rng.choice(["u", "v", "w"])
    t = rng.randrange(len(d[name]))
    i = rng.randrange(9)
    d[name][t][i] = rng.choice([-1, 0, 1])
    return d


def plus(data, rng):
    """Add a random ternary product term (rank +1)."""
    d = deepcopy(data)
    d["u"].append([rng.choice([-1, 0, 1]) for _ in range(9)])
    d["v"].append([rng.choice([-1, 0, 1]) for _ in range(9)])
    d["w"].append([rng.choice([-1, 0, 1]) for _ in range(9)])
    return d


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 50000
    rng = random.Random(seed)
    cur = schoolbook()
    assert brent_residual(cur["u"], cur["v"], cur["w"]) == 0
    best23 = None
    best23_s = 10**9
    res = 0
    for step in range(steps):
        if rng.random() < 0.05:
            cand = plus(cur, rng)
        else:
            cand = flip(cur, rng)
        new_res = brent_residual(cand["u"], cand["v"], cand["w"])
        # accept if residual not worse, or with small probability
        if new_res <= res or rng.random() < 0.01:
            cur = cand
            res = new_res
            if res == 0:
                c = compact_rank(cur)
                rnk = len(c["u"])
                if rnk == 23:
                    s = support(c)
                    if s < best23_s:
                        best23 = c
                        best23_s = s
                        print(f"step {step}: rank23 support={best23_s}")
                elif rnk < 23:
                    print(f"step {step}: rank {rnk} support={support(c)} (!)")
                    best23 = c
                    best23_s = support(c)
                    break
        if step % 10000 == 0:
            c = compact_rank(cur)
            print(f"step {step}: residual={res} rank~={len(c['u'])} best23={best23_s}")
    out = Path("submissions/attempt014-flipgraph/solution.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    if best23 is None:
        print("no rank-23 scheme found")
        return 1
    out.write_text(json.dumps(best23, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} rank={len(best23['u'])} support={best23_s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
