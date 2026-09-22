#!/usr/bin/env python3
"""Additions search: mutate Sun U/V, solve unique W, multi-seed CSE cost + histogram.

Note: for Sun (and Stapleton), Brent determines W uniquely from U,V — nullspace
dim = 0. So we cannot vary W alone. This tool mutates ternary U/V entries,
re-solves W, and scores certified SLP cost = CSE(U)+CSE(V)+CSE(W).

  python3 -u tools/slp_w_affine.py --trials 2000 --seed 0 \\
      --log logs/w-affine-smoke.log --out submissions/attempt017-w-affine
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from pathlib import Path


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


def target(a, b, c) -> Fraction:
    row, inner = divmod(a, 3)
    b_inner, col = divmod(b, 3)
    return Fraction(1 if inner == b_inner and c == 3 * col + row else 0)


def solve_w(u, v):
    """Exact W solve over Q (Fraction). Free vars set to 0."""
    rank = len(u)
    W = [[Fraction(0)] * 9 for _ in range(rank)]
    n_free = 0
    for c in range(9):
        M = []
        for a in range(9):
            for b in range(9):
                M.append(
                    [Fraction(u[t][a] * v[t][b]) for t in range(rank)]
                    + [target(a, b, c)]
                )
        r = 0
        pivot_col = [-1] * rank
        for col in range(rank):
            piv = None
            for i in range(r, 81):
                if M[i][col] != 0:
                    piv = i
                    break
            if piv is None:
                n_free += 1
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
        for i in range(81):
            if all(M[i][j] == 0 for j in range(rank)) and M[i][rank] != 0:
                return None, n_free
        for col in range(rank):
            if pivot_col[col] >= 0:
                W[col][c] = M[pivot_col[col]][rank]
            else:
                W[col][c] = Fraction(0)
    return W, n_free


def to_int_ternary(W):
    out = []
    for row in W:
        r = []
        for x in row:
            if x.denominator != 1:
                return None
            xi = int(x)
            if abs(xi) > 1:
                return None
            r.append(xi)
        out.append(r)
    return out


def greedy_cse(targets, rng, max_extract=40):
    dim = len(targets[0])
    exprs = []
    for t in targets:
        terms = [(i, t[i]) for i in range(dim) if t[i] != 0]
        if any(abs(c) != 1 for _, c in terms):
            return None
        exprs.append(terms)
    inter = []

    def pair_key(i, si, j, sj):
        return (i, si, j, sj) if (i, si) <= (j, sj) else (j, sj, i, si)

    for _ in range(max_extract):
        counts = Counter()
        locations = {}
        for ei, expr in enumerate(exprs):
            if len(expr) < 2:
                continue
            seen_local = set()
            for (a, sa), (b, sb) in combinations(expr, 2):
                key = pair_key(a, sa, b, sb)
                if key in seen_local:
                    continue
                seen_local.add(key)
                counts[key] += 1
                locations.setdefault(key, []).append(ei)
        cands = [k for k, c in counts.items() if c >= 2]
        if not cands:
            break
        cands.sort(key=lambda k: (-counts[k], rng.random()))
        top = counts[cands[0]]
        key = rng.choice([k for k in cands if counts[k] == top])
        a, sa, b, sb = key
        s_inner = sb * sa
        new_idx = dim + len(inter)
        inter.append((a, s_inner, b))
        for ei in locations[key]:
            expr = exprs[ei]
            new_expr = []
            ra = rb = False
            for n, s in expr:
                if not ra and n == a and s == sa:
                    ra = True
                    continue
                if not rb and n == b and s == sb:
                    rb = True
                    continue
                new_expr.append((n, s))
            if ra and rb:
                new_expr.append((new_idx, sa))
                exprs[ei] = new_expr
    side = {"base_dim": dim, "inter": inter, "final": [list(e) for e in exprs]}
    out, _ = expand(side)
    if out != list(targets):
        return None
    return side


def hill_w_to_cols(w_hill):
    return [
        tuple(w_hill[r][3 * j + i] for r in range(len(w_hill)))
        for i in range(3)
        for j in range(3)
    ]


def naive_form_cost(vectors) -> int:
    """Upper bound: no shared intermediates, cost = sum max(nnz-1, 0)."""
    total = 0
    for v in vectors:
        nnz = sum(1 for x in v if x != 0)
        if any(abs(x) > 1 for x in v):
            return 10**9
        total += max(nnz - 1, 0)
    return total


def multi_seed_cse(targets, n_seeds, base_seed, max_nnz=10):
    # Skip pathological dense forms (CSE pair enumeration explodes).
    if any(sum(1 for x in t if x != 0) > max_nnz for t in targets):
        return None, None
    best_side, best_c = None, 10**9
    for s in range(n_seeds):
        side = greedy_cse(targets, random.Random(base_seed * 10007 + s))
        if side is None:
            continue
        c = cost(side)
        if c < best_c:
            best_c, best_side = c, side
    return best_c if best_side is not None else None, best_side


def score_uvw(u, v, w, n_seeds, base_seed):
    u_t = [tuple(r) for r in u]
    v_t = [tuple(r) for r in v]
    w_t = hill_w_to_cols(w)
    # Fast reject only hopelessly dense mutations (Sun naive≈120 before CSE).
    naive = naive_form_cost(u_t) + naive_form_cost(v_t) + naive_form_cost(w_t)
    if naive > 160:
        return None, None
    cu, su = multi_seed_cse(u_t, n_seeds, base_seed)
    cv, sv = multi_seed_cse(v_t, n_seeds, base_seed + 1)
    cw, sw = multi_seed_cse(w_t, n_seeds, base_seed + 2)
    if None in (cu, cv, cw):
        return None, None
    sides = {"U": su, "V": sv, "W": sw}
    return cu + cv + cw, sides


def nz_positions(M):
    return [(t, i) for t, row in enumerate(M) for i, x in enumerate(row) if x != 0]


def atomic_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_out(out_dir: Path, u, v, w, sides, meta):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "solution.json").write_text(
        json.dumps({"u": u, "v": v, "w": w}, separators=(",", ":")), encoding="utf-8"
    )
    (out_dir / "sides.json").write_text(json.dumps(sides, indent=2), encoding="utf-8")
    cert = {
        **meta,
        "brent_ok": brent_ok(u, v, w),
        "rank": len(u),
        "support": sum(x != 0 for M in (u, v, w) for row in M for x in row),
        "breakdown": {
            "U": cost(sides["U"]),
            "V": cost(sides["V"]),
            "W": cost(sides["W"]),
        },
        "certified_cost": cost(sides["U"]) + cost(sides["V"]) + cost(sides["W"]),
    }
    (out_dir / "slp_certificate.json").write_text(
        json.dumps(cert, indent=2), encoding="utf-8"
    )
    return cert


def hist_summary(hist: Counter, total_n: int):
    if total_n == 0:
        return "empty"
    items = sorted(hist.items())
    parts = [f"{k}:{v}" for k, v in items[:12]]
    le56 = sum(v for k, v in hist.items() if k <= 56)
    return f"{{{', '.join(parts)}}} le56={le56}/{total_n} ({100 * le56 / total_n:.2f}%)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--trials", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cse-seeds", type=int, default=3)
    ap.add_argument("--status-every", type=int, default=2000)
    ap.add_argument("--checkpoint-secs", type=float, default=600.0)
    ap.add_argument("--log", type=Path, default=Path("logs/w-affine.log"))
    ap.add_argument("--out", type=Path, default=Path("submissions/attempt017-w-affine"))
    ap.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("logs/checkpoints/affine_checkpoint.json"),
    )
    ap.add_argument("--resume", type=Path, default=None)
    ap.add_argument("--start-t", type=int, default=1)
    ap.add_argument("--sterile-after", type=int, default=200_000)
    ap.add_argument("--max-edits", type=int, default=3)
    args = ap.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)

    start_t = args.start_t
    if args.resume and args.resume.exists():
        ck = json.loads(args.resume.read_text(encoding="utf-8"))
        start_t = int(ck.get("resume_from_t") or (int(ck.get("last_t", 0)) + 1))
        if "seed" in ck:
            args.seed = int(ck["seed"])
        if "trials_target" in ck and args.trials == 200_000:
            args.trials = int(ck["trials_target"])

    data = json.loads(args.sun.read_text(encoding="utf-8"))
    u0, v0, w0 = data["u"], data["v"], data["w"]
    assert brent_ok(u0, v0, w0)
    Ww, n_free = solve_w(u0, v0)
    assert Ww is not None

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    base_total, base_sides = score_uvw(u0, v0, w0, max(args.cse_seeds, 6), args.seed)
    if base_sides is None:
        log("ERROR baseline CSE failed")
        return 2
    # Prefer literature Sun 56 if greedy rebuild is worse
    best_total = min(base_total, 56)
    best_uvw = (u0, v0, w0)
    best_sides = base_sides
    hist: Counter = Counter({base_total: 1})
    scored = 1
    solved_ok = 0
    improvements = 0

    log(
        f"affine/uv-mutate start free_vars_W={n_free} "
        f"(0 => W unique given U,V; mutating U/V) "
        f"greedy_baseline={base_total} track_best={best_total} "
        f"trials={args.trials} seed={args.seed} start_t={start_t}"
    )
    if start_t == 1:
        write_out(
            args.out,
            u0,
            v0,
            w0,
            best_sides,
            {
                "note": f"Sun start; greedy_CSE={base_total}; lit_ref=56",
                "improved": False,
                "greedy_baseline": base_total,
            },
        )

    t0 = time.time()
    last_ck = t0

    def save_ck(t):
        atomic_checkpoint(
            args.checkpoint,
            {
                "job": "slp_w_affine",
                "seed": args.seed,
                "trials_target": args.trials,
                "last_t": t,
                "best_total": best_total,
                "scored": scored,
                "solved_ok": solved_ok,
                "improvements": improvements,
                "hist": {str(k): v for k, v in hist.items()},
                "resume_from_t": t + 1,
                "out": str(args.out),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    for t in range(start_t, args.trials + 1):
        rng = random.Random(args.seed * 1_000_003 + t)
        u = [row[:] for row in u0]
        v = [row[:] for row in v0]
        # Mutate 1..max_edits nonzero U/V entries to ternary
        k = rng.randint(1, args.max_edits)
        for _ in range(k):
            which = rng.choice(["u", "v"])
            M = u if which == "u" else v
            nz = nz_positions(M)
            if not nz:
                continue
            ti, ii = rng.choice(nz)
            M[ti][ii] = rng.choice([0, 1, -1])
        Ww, _ = solve_w(u, v)
        if Ww is None:
            continue
        w = to_int_ternary(Ww)
        if w is None:
            continue
        if not brent_ok(u, v, w):
            continue
        solved_ok += 1
        total, sides = score_uvw(u, v, w, args.cse_seeds, args.seed * 19 + t)
        if sides is None:
            continue
        hist[total] += 1
        scored += 1
        if total < best_total:
            improvements += 1
            log(
                f"IMPROVED t={t} total {best_total} -> {total} "
                f"(U={cost(sides['U'])} V={cost(sides['V'])} W={cost(sides['W'])}) "
                f"support={sum(x!=0 for M in (u,v,w) for row in M for x in row)}"
            )
            best_total = total
            best_uvw = (u, v, w)
            best_sides = sides
            cert = write_out(
                args.out,
                u,
                v,
                w,
                sides,
                {"note": f"uv-mutate trial={t}", "improved": True, "trial": t},
            )
            if not cert["brent_ok"]:
                log("ERROR brent false")
                return 2
            if best_total <= 55:
                log(f"HIT TARGET total={best_total}")
            save_ck(t)

        now = time.time()
        if t % args.status_every == 0 or (now - last_ck) >= args.checkpoint_secs:
            elapsed = now - t0
            vals = sorted(hist.elements())
            p50 = vals[len(vals) // 2] if vals else None
            log(
                f"status t={t} best_total={best_total} scored={scored} "
                f"solved_ok={solved_ok} improvements={improvements} p50={p50} "
                f"hist={hist_summary(hist, scored)} elapsed_s={elapsed:.1f}"
            )
            save_ck(t)
            last_ck = now
            if (
                scored >= args.sterile_after
                and best_total >= 57
                and sum(v for k, v in hist.items() if k <= 56) == 0
            ):
                log(f"STERILE stop scored={scored} best={best_total}")
                return 1

    elapsed = time.time() - t0
    log(
        f"done best_total={best_total} scored={scored} improvements={improvements} "
        f"hist={hist_summary(hist, scored)} elapsed_s={elapsed:.1f}"
    )
    save_ck(args.trials)
    return 0 if best_total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
