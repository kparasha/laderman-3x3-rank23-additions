#!/usr/bin/env python3
"""Rank of 729×23 product matrix over GF(2) (and GF(3) sanity)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from support_overnight import brent_ok  # noqa: E402


def product_matrix_mod(data, p: int):
    u, v, w = data["u"], data["v"], data["w"]
    cols = []
    for t in range(len(u)):
        col = []
        for a in range(9):
            for b in range(9):
                for c in range(9):
                    col.append((u[t][a] * v[t][b] * w[t][c]) % p)
        cols.append(col)
    return cols  # list of 23 columns, length 729


def rank_mod_p(cols, p: int) -> int:
    """cols: list of n vectors length m over 0..p-1."""
    m = len(cols[0])
    n = len(cols)
    mat = [[cols[j][i] for j in range(n)] for i in range(m)]
    r = 0
    for col in range(n):
        piv = None
        for i in range(r, m):
            if mat[i][col] % p != 0:
                piv = i
                break
        if piv is None:
            continue
        mat[r], mat[piv] = mat[piv], mat[r]
        inv = pow(mat[r][col] % p, -1, p) if p > 1 else 1
        for i in range(m):
            if i != r and mat[i][col] % p != 0:
                fac = (mat[i][col] * inv) % p
                for j in range(n):
                    mat[i][j] = (mat[i][j] - fac * mat[r][j]) % p
        r += 1
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-gf2"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rows = {}
    for src in args.src:
        data = json.loads(src.read_text(encoding="utf-8"))
        assert brent_ok(*[data[k] for k in ("u", "v", "w")])
        cols = product_matrix_mod(data, 2)
        r2 = rank_mod_p(cols, 2)
        cols3 = product_matrix_mod(data, 3)
        r3 = rank_mod_p(cols3, 3)
        rows[str(src)] = {"rank_gf2": r2, "rank_gf3": r3, "terms": len(data["u"])}
    best = min(min(v["rank_gf2"], v["rank_gf3"]) for v in rows.values())
    summary = {"schemes": rows, "best_mod_rank": best, "improved": best < 23}
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
