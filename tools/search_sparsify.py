#!/usr/bin/env python3
"""Try to reduce support of a rank-23 UVW scheme by zeroing ternary coeffs."""

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


def nonzero_positions(u, v, w):
    out = []
    for name, M in (("u", u), ("v", v), ("w", w)):
        for t, row in enumerate(M):
            for i, x in enumerate(row):
                if x != 0:
                    out.append((name, t, i, x))
    return out


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "submissions/stapleton60/solution.json")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "submissions/current/solution.json")
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
    rng = random.Random(seed)
    data = json.loads(src.read_text(encoding="utf-8"))
    u, v, w = data["u"], data["v"], data["w"]
    assert brent_ok(u, v, w)
    best = deepcopy(data)
    best_s = support(u, v, w)
    print(f"start support={best_s}")
    improved = 0
    for r in range(rounds):
        name, t, i, old = rng.choice(nonzero_positions(u, v, w))
        M = {"u": u, "v": v, "w": w}[name]
        # try zero, or flip sign, or set to other ternary
        candidates = [0, 1, -1]
        rng.shuffle(candidates)
        for new in candidates:
            if new == old:
                continue
            M[t][i] = new
            if brent_ok(u, v, w):
                s = support(u, v, w)
                if s < best_s:
                    best = {"u": deepcopy(u), "v": deepcopy(v), "w": deepcopy(w)}
                    best_s = s
                    improved += 1
                    print(f"round {r}: support -> {best_s}")
                break
            M[t][i] = old
        else:
            M[t][i] = old
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(best, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} support={best_s} improvements={improved}")
    return 0 if best_s < support(data["u"], data["v"], data["w"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
