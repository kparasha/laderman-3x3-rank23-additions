#!/usr/bin/env python3
"""Given U,V, solve Brent equations linearly for W (over Q), seek lower support."""

from __future__ import annotations

import json
import random
import sys
from fractions import Fraction
from pathlib import Path


def target(a, b, c):
    row, inner = divmod(a, 3)
    b_inner, col = divmod(b, 3)
    return Fraction(1 if inner == b_inner and c == 3 * col + row else 0)


def solve_w(u, v):
    """Solve for W[t][c] such that sum_t U[t,a]V[t,b]W[t,c] = target.
    For each c, this is a linear system in the 23 unknowns W[*,c].
    """
    rank = len(u)
    # For each c independently: equations indexed by (a,b)
    W = [[Fraction(0)] * 9 for _ in range(rank)]
    for c in range(9):
        # Build 81 x 23 matrix
        rows = []
        rhs = []
        for a in range(9):
            for b in range(9):
                rows.append([Fraction(u[t][a] * v[t][b]) for t in range(rank)])
                rhs.append(target(a, b, c))
        # Gaussian elimination
        M = [rows[i][:] + [rhs[i]] for i in range(81)]
        r = 0
        pivot_col = [-1] * rank
        for col in range(rank):
            piv = None
            for i in range(r, 81):
                if M[i][col] != 0:
                    piv = i
                    break
            if piv is None:
                continue
            M[r], M[piv] = M[piv], M[r]
            fac = M[r][col]
            M[r] = [x / fac for x in M[r]]
            for i in range(81):
                if i == r:
                    continue
                fac = M[i][col]
                if fac != 0:
                    M[i] = [M[i][j] - fac * M[r][j] for j in range(rank + 1)]
            pivot_col[col] = r
            r += 1
        # Check consistency
        for i in range(81):
            if all(M[i][j] == 0 for j in range(rank)) and M[i][rank] != 0:
                return None
        # Read solution (free vars = 0)
        for col in range(rank):
            if pivot_col[col] >= 0:
                W[col][c] = M[pivot_col[col]][rank]
            else:
                W[col][c] = Fraction(0)
    return W


def to_int(W):
    out = []
    for row in W:
        r = []
        for x in row:
            if x.denominator != 1:
                return None
            r.append(int(x))
        out.append(r)
    return out


def support(u, v, w):
    return sum(x != 0 for M in (u, v, w) for row in M for x in row)


def brent_ok_int(u, v, w):
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(len(u)))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                if s != int(inner == b_inner and c == 3 * col + row):
                    return False
    return True


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
    rng = random.Random(seed)
    data = json.loads(src.read_text(encoding="utf-8"))
    u, v = data["u"], data["v"]
    W0 = solve_w(u, v)
    assert W0 is not None
    w = to_int(W0)
    assert w is not None and brent_ok_int(u, v, w)
    best = {"u": u, "v": v, "w": w}
    best_s = support(u, v, w)
    print(f"start support={best_s}")

    for r in range(rounds):
        cu = [row[:] for row in best["u"]]
        cv = [row[:] for row in best["v"]]
        # mutate one nonzero in U or V to 0 or flip
        which = rng.choice(["u", "v"])
        M = cu if which == "u" else cv
        nz = [(t, i) for t, row in enumerate(M) for i, x in enumerate(row) if x != 0]
        if not nz:
            continue
        t, i = rng.choice(nz)
        old = M[t][i]
        M[t][i] = rng.choice([0, 1, -1, old])
        Ww = solve_w(cu, cv)
        if Ww is None:
            continue
        wi = to_int(Ww)
        if wi is None:
            continue
        # allow coefficients with |x|<=2 as mild relaxation then skip if >1 for ternary preference
        if any(abs(x) > 2 for row in wi for x in row):
            continue
        if not brent_ok_int(cu, cv, wi):
            continue
        s = support(cu, cv, wi)
        if s < best_s:
            best = {"u": cu, "v": cv, "w": wi}
            best_s = s
            print(f"round {r}: support -> {best_s}")
        elif s == best_s and rng.random() < 0.02:
            best = {"u": cu, "v": cv, "w": wi}

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(best, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} support={best_s}")


if __name__ == "__main__":
    main()
