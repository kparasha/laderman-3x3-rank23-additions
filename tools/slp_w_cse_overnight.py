#!/usr/bin/env python3
"""Overnight W-side CSE: beat Sun 56 by driving W 30→29 (U/V stay certified 13).

Sun claims U,V ≥ 13 on this factorization, so total < 56 almost certainly means
W ≤ 29. This search:

  - Freezes Sun U/V SLP schedules at cost 13+13.
  - Applies product sign-flips (U[t],W[t] or V[t],W[t] *= ±1) that preserve Brent;
    U/V SLP finals are negated in place (cost unchanged).
  - Rebuilds only W via random-tiebreak greedy CSE on the (signed) W columns.
  - Also probes pure W CSE on the unflipped Sun columns (many seeds).

Cost model = Sun's. Writes best under --out on every improvement.

  python3 -u tools/slp_w_cse_overnight.py --trials 8000000 --seed 42 \\
      --log logs/w-cse-overnight.log --out submissions/attempt016-w-mutate
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import Counter
from copy import deepcopy
from itertools import combinations
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


def cost(side) -> int:
    extra = sum(max(sum(abs(c) for _, c in f) - 1, 0) for f in side["final"])
    return len(side["inter"]) + extra


def sun_uvw_hill(u_side, v_side, w_side):
    U = [list(r) for r in expand(u_side)[0]]
    V = [list(r) for r in expand(v_side)[0]]
    W_cols = expand(w_side)[0]
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


def negate_final(side, t: int):
    """Flip sign of product t in an SLP final list (cost unchanged)."""
    side["final"][t] = [(idx, -c) for idx, c in side["final"][t]]


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


def hill_w_to_sun_cols(w_hill):
    return [
        tuple(w_hill[r][3 * j + i] for r in range(23))
        for i in range(3)
        for j in range(3)
    ]


def factors_from_sun():
    return sun_uvw_hill(SIDES0["U"], SIDES0["V"], SIDES0["W"])


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


def atomic_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--log", type=Path, default=Path("logs/w-cse-overnight.log"))
    ap.add_argument("--out", type=Path, default=Path("submissions/attempt016-w-mutate"))
    ap.add_argument("--status-every", type=int, default=1000)
    ap.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("logs/checkpoints/cse_checkpoint.json"),
        help="Atomic local resume file (no network)",
    )
    ap.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Resume from checkpoint JSON (continues trials after last_t)",
    )
    ap.add_argument(
        "--start-t",
        type=int,
        default=1,
        help="First trial index (1-based); overridden by --resume",
    )
    ap.add_argument(
        "--flip-prob",
        type=float,
        default=0.35,
        help="Per-product flip probability for sign_UW / sign_VW modes",
    )
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

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def save_ck(t, best_total, valid, improvements, elapsed):
        atomic_checkpoint(
            args.checkpoint,
            {
                "job": "slp_w_cse_overnight",
                "seed": args.seed,
                "trials_target": args.trials,
                "last_t": t,
                "best_total": best_total,
                "valid": valid,
                "improvements": improvements,
                "elapsed_s": elapsed,
                "resume_from_t": t + 1,
                "out": str(args.out),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    u0, v0, w0 = factors_from_sun()
    assert brent_ok(u0, v0, w0)
    best_sides = {
        "U": deepcopy(SIDES0["U"]),
        "V": deepcopy(SIDES0["V"]),
        "W": deepcopy(SIDES0["W"]),
    }
    best_total = 56
    # Reload best artifact if resuming and an improved cert already exists
    cert_path = args.out / "slp_certificate.json"
    if cert_path.exists():
        try:
            prev = json.loads(cert_path.read_text(encoding="utf-8"))
            if prev.get("certified_cost", 56) < best_total and prev.get("brent_ok"):
                best_total = int(prev["certified_cost"])
        except Exception:
            pass

    log(
        f"baseline total=56 (U/V frozen 13+13, W=30); "
        f"trials={args.trials} seed={args.seed} flip_prob={args.flip_prob} "
        f"start_t={start_t}"
    )
    if start_t == 1:
        write_out(
            args.out, u0, v0, w0, best_sides, {"note": "Sun baseline", "improved": False}
        )

    t0 = time.time()
    improvements = 0
    valid = 0

    for t in range(start_t, args.trials + 1):
        rng = random.Random(args.seed * 1_000_003 + t)
        # Bias toward W-only / single-side flips; U/V SLP cost stays 13.
        mode = rng.choices(
            ["W_only", "sign_UW", "sign_VW", "sign_both"],
            weights=[2, 4, 4, 2],
            k=1,
        )[0]

        sideU = deepcopy(SIDES0["U"])
        sideV = deepcopy(SIDES0["V"])
        u = [row[:] for row in u0]
        v = [row[:] for row in v0]
        w = [row[:] for row in w0]

        if mode in ("sign_UW", "sign_both"):
            for i in range(23):
                if rng.random() < args.flip_prob:
                    u[i] = [-x for x in u[i]]
                    w[i] = [-x for x in w[i]]
                    negate_final(sideU, i)
        if mode in ("sign_VW", "sign_both"):
            for i in range(23):
                if rng.random() < args.flip_prob:
                    v[i] = [-x for x in v[i]]
                    w[i] = [-x for x in w[i]]
                    negate_final(sideV, i)

        # U/V must still expand to the signed factors (cheap sanity).
        if expand(sideU)[0] != [tuple(r) for r in u]:
            continue
        if expand(sideV)[0] != [tuple(r) for r in v]:
            continue
        if not brent_ok(u, v, w):
            continue

        sideW = greedy_cse(hill_w_to_sun_cols(w), rng)
        if sideW is None:
            continue
        valid += 1
        total = cost(sideU) + cost(sideV) + cost(sideW)  # 13+13+W
        assert cost(sideU) == 13 and cost(sideV) == 13

        if total < best_total:
            try:
                uu, vv, ww = sun_uvw_hill(sideU, sideV, sideW)
            except Exception:
                continue
            if not brent_ok(uu, vv, ww):
                continue
            improvements += 1
            w_cost = cost(sideW)
            log(
                f"IMPROVED t={t} mode={mode} total {best_total} -> {total} "
                f"(U=13 V=13 W={w_cost})"
            )
            best_total = total
            best_sides = {"U": sideU, "V": sideV, "W": sideW}
            cert = write_out(
                args.out,
                uu,
                vv,
                ww,
                best_sides,
                {
                    "note": f"mode={mode} trial={t}",
                    "improved": True,
                    "trial": t,
                    "mode": mode,
                },
            )
            if not cert["brent_ok"]:
                log("ERROR brent false")
                return 2
            if best_total <= 55:
                log(f"HIT TARGET total={best_total} W={w_cost}")

        if t % args.status_every == 0:
            elapsed = time.time() - t0
            log(
                f"status t={t} best_total={best_total} valid={valid} "
                f"improvements={improvements} elapsed_s={elapsed:.1f}"
            )
            save_ck(t, best_total, valid, improvements, elapsed)

    elapsed = time.time() - t0
    log(
        f"done best_total={best_total} valid={valid} improvements={improvements} "
        f"elapsed_s={elapsed:.1f}"
    )
    save_ck(args.trials, best_total, valid, improvements, elapsed)
    return 0 if best_total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
