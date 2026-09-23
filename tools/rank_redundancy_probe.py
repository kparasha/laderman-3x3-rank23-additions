#!/usr/bin/env python3
"""Test whether any rank-1 product is a Q-linear combo of the other 22.

If so, delete that term and repair to obtain exact rank < 23.

  python3 -u tools/rank_redundancy_probe.py submissions/sun56/solution.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from fractions import Fraction
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


def product_vector(u, v, w, t):
    out = []
    for a in range(9):
        for b in range(9):
            for c in range(9):
                out.append(Fraction(u[t][a] * v[t][b] * w[t][c]))
    return out


def in_span(target, columns):
    """Solve columns * alpha = target over Q; columns is list of 729-vectors."""
    m = len(target)
    n = len(columns)
    # Augmented matrix n+1 columns
    M = [[columns[j][i] for j in range(n)] + [target[i]] for i in range(m)]
    r = 0
    pivot = [-1] * n
    for col in range(n):
        piv = None
        for i in range(r, m):
            if M[i][col] != 0:
                piv = i
                break
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        fac = M[r][col]
        M[r] = [x / fac for x in M[r]]
        for i in range(m):
            if i == r:
                continue
            fac = M[i][col]
            if fac != 0:
                M[i] = [M[i][j] - fac * M[r][j] for j in range(n + 1)]
        pivot[col] = r
        r += 1
    for i in range(m):
        if all(M[i][j] == 0 for j in range(n)) and M[i][n] != 0:
            return False, None
    alpha = [Fraction(0)] * n
    for col in range(n):
        if pivot[col] >= 0:
            alpha[col] = M[pivot[col]][n]
    return True, alpha


def drop_and_check(data, t):
    u = [r[:] for i, r in enumerate(data["u"]) if i != t]
    v = [r[:] for i, r in enumerate(data["v"]) if i != t]
    w = [r[:] for i, r in enumerate(data["w"]) if i != t]
    return {"u": u, "v": v, "w": w}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-redundancy"))
    ap.add_argument("--log", type=Path, default=Path("logs/rank-redundancy-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    assert brent_ok(data["u"], data["v"], data["w"])
    rank = len(data["u"])

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start src={args.src} rank={rank}")
    t0 = time.time()
    hits = []
    for t in range(rank):
        target = product_vector(data["u"], data["v"], data["w"], t)
        cols = [
            product_vector(data["u"], data["v"], data["w"], s)
            for s in range(rank)
            if s != t
        ]
        ok, alpha = in_span(target, cols)
        if not ok:
            continue
        # Coefficients must be integers in {-1,0,1}? not required for redundancy test
        reduced = drop_and_check(data, t)
        res = brent_ok(reduced["u"], reduced["v"], reduced["w"])
        hits.append(
            {
                "t": t,
                "alpha_max_den": max(a.denominator for a in alpha),
                "drop_brent_ok": res,
                "new_rank": len(reduced["u"]),
            }
        )
        log(f"REDUNDANT t={t} drop_brent={res} alpha_sample={alpha[:5]}")

    elapsed = time.time() - t0
    summary = {
        "src": str(args.src),
        "rank": rank,
        "redundant_terms": len(hits),
        "hits": hits,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if hits and any(h["drop_brent_ok"] for h in hits):
        t_hit = next(h["t"] for h in hits if h["drop_brent_ok"])
        out_data = drop_and_check(data, t_hit)
        (args.out / "solution.json").write_text(
            json.dumps(out_data, separators=(",", ":")), encoding="utf-8"
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
