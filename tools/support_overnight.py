#!/usr/bin/env python3
"""Overnight support search from Stapleton: orbit + 2/3-edit ternary mutations.

Goes beyond prior single-zero / double-flip tries by:
  0) discrete automorphism orbit (transpose + cyclic index actions)
  1) exhaustive single-zero pass
  2) random 2-edit and 3-edit ternary mutations with accept-rate logging

  python3 -u tools/support_overnight.py --edits 10000 --seed 0 \\
      --log logs/support-smoke.log --out submissions/attempt018-support
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from copy import deepcopy
from itertools import permutations
from pathlib import Path


def brent_ok(u, v, w) -> bool:
    rank = len(u)
    for a in range(9):
        for b in range(9):
            for c in range(9):
                s = sum(u[t][a] * v[t][b] * w[t][c] for t in range(rank))
                row, inner = divmod(a, 3)
                b_inner, col = divmod(b, 3)
                if s != int(inner == b_inner and c == 3 * col + row):
                    return False
    return True


def support(u, v, w) -> int:
    return sum(x != 0 for M in (u, v, w) for row in M for x in row)


def mats(data):
    return data["u"], data["v"], data["w"]


def pack(u, v, w):
    return {"u": u, "v": v, "w": w}


def positions(u, v, w):
    out = []
    for name, M in (("u", u), ("v", v), ("w", w)):
        for t, row in enumerate(M):
            for i, x in enumerate(row):
                if x != 0:
                    out.append((name, t, i))
    return out


def getv(data, name, t, i):
    return data[name][t][i]


def setv(data, name, t, i, val):
    data[name][t][i] = val


def remap9(vec, perm):
    return [vec[perm[i]] for i in range(9)]


def transpose_scheme(data):
    """Swap U/V and transpose each 3×3 factor (A,B)->(B^T,A^T) style dual."""

    def t9(row):
        return [row[3 * j + i] for i in range(3) for j in range(3)]

    u, v, w = mats(data)
    return pack([t9(r) for r in v], [t9(r) for r in u], [t9(r) for r in w])


def relabel_digits(data, perm3):
    """Apply S3 perm to {0,1,2} on both axes of every 3×3 factor block."""

    def p9(row):
        out = [0] * 9
        for i in range(3):
            for j in range(3):
                out[3 * perm3[i] + perm3[j]] = row[3 * i + j]
        return out

    u, v, w = mats(data)
    return pack([p9(r) for r in u], [p9(r) for r in v], [p9(r) for r in w])


def cycle_factors(data, k: int):
    """Cycle the three bilinear modes k times (discrete tensor symmetry attempt)."""
    u, v, w = mats(data)
    for _ in range(k % 3):
        # (U,V,W) -> (V, W_as_U-shaped, U) with index remap W[t][c] -> row layout
        nu = [r[:] for r in v]
        nv = []
        for t in range(len(w)):
            # interpret W row as 3x3 and read as V-style
            nv.append(w[t][:])
        nw = [r[:] for r in u]
        u, v, w = nu, nv, nw
    return pack(u, v, w)


def s3_perms():
    return [list(p) for p in permutations(range(3))]


def orbit_seeds(data):
    """Discrete orbit: id, transpose, S3 digit relabel, factor cycles."""
    out = []
    seen = set()

    def add(d, tag):
        if not brent_ok(*mats(d)):
            return
        key = json.dumps(d, separators=(",", ":"))
        if key in seen:
            return
        seen.add(key)
        out.append((support(*mats(d)), tag, d))

    add(deepcopy(data), "id")
    tr = transpose_scheme(data)
    add(tr, "transpose")
    for p in s3_perms():
        add(relabel_digits(data, p), f"s3:{p}")
        add(relabel_digits(tr, p), f"transpose+s3:{p}")
    for k in (1, 2):
        cyc = cycle_factors(data, k)
        add(cyc, f"cycle{k}")
        add(transpose_scheme(cyc), f"cycle{k}+transpose")
        for p in s3_perms():
            add(relabel_digits(cyc, p), f"cycle{k}+s3:{p}")

    out.sort(key=lambda x: x[0])
    return out


def exhaustive_zero(best):
    cur = deepcopy(best)
    best_s = support(*mats(best))
    changed = True
    zeros = 0
    while changed:
        changed = False
        for name, t, i in positions(*mats(cur)):
            old = getv(cur, name, t, i)
            setv(cur, name, t, i, 0)
            if brent_ok(*mats(cur)):
                s = support(*mats(cur))
                if s < best_s:
                    best = deepcopy(cur)
                    best_s = s
                    changed = True
                    zeros += 1
                    break
            setv(cur, name, t, i, old)
        cur = deepcopy(best)
    return best, zeros


def atomic_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_out(out_dir: Path, data, meta):
    out_dir.mkdir(parents=True, exist_ok=True)
    u, v, w = mats(data)
    (out_dir / "solution.json").write_text(
        json.dumps(data, separators=(",", ":")), encoding="utf-8"
    )
    cert = {
        **meta,
        "brent_ok": brent_ok(u, v, w),
        "rank": len(u),
        "support": support(u, v, w),
    }
    (out_dir / "support_certificate.json").write_text(
        json.dumps(cert, indent=2), encoding="utf-8"
    )
    return cert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--src", type=Path, default=Path("submissions/stapleton60/solution.json")
    )
    ap.add_argument("--out", type=Path, default=Path("submissions/attempt018-support"))
    ap.add_argument("--edits", type=int, default=2_000_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--status-every", type=int, default=20000)
    ap.add_argument("--checkpoint-secs", type=float, default=600.0)
    ap.add_argument("--log", type=Path, default=Path("logs/support-overnight.log"))
    ap.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("logs/checkpoints/support_checkpoint.json"),
    )
    ap.add_argument("--resume", type=Path, default=None)
    ap.add_argument("--start-e", type=int, default=1)
    ap.add_argument("--p3", type=float, default=0.35, help="Prob of 3-edit vs 2-edit")
    args = ap.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)

    start_e = args.start_e
    if args.resume and args.resume.exists():
        ck = json.loads(args.resume.read_text(encoding="utf-8"))
        start_e = int(ck.get("resume_from_e") or (int(ck.get("last_e", 0)) + 1))
        if "seed" in ck:
            args.seed = int(ck["seed"])
        if "edits_target" in ck and args.edits == 2_000_000:
            args.edits = int(ck["edits_target"])

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    base = json.loads(args.src.read_text(encoding="utf-8"))
    assert brent_ok(*mats(base))
    log(f"orbit: expanding from support={support(*mats(base))}")
    orb = orbit_seeds(base)
    log(f"orbit: {len(orb)} Brent-ok schemes; best={orb[0][0]} ({orb[0][1]})")
    best = deepcopy(orb[0][2])
    # Also try loading previous out if better
    prev = args.out / "solution.json"
    if prev.exists():
        try:
            cand = json.loads(prev.read_text(encoding="utf-8"))
            if brent_ok(*mats(cand)) and support(*mats(cand)) < support(*mats(best)):
                best = cand
                log(f"resumed best from out support={support(*mats(best))}")
        except Exception:
            pass

    best, nzero = exhaustive_zero(best)
    best_s = support(*mats(best))
    log(f"after single-zero: support={best_s} zeros_applied={nzero}")
    if start_e == 1:
        write_out(
            args.out,
            best,
            {"note": "orbit+single-zero seed", "improved": best_s < 152},
        )

    rng = random.Random(args.seed)
    # Advance RNG deterministically for resume by skipping edit draws is hard;
    # use per-edit seed instead.
    brent_ok_n = 0
    tried = 0
    improved = 0
    equal_keep = 0
    t0 = time.time()
    last_ck = t0

    def save_ck(e):
        atomic_checkpoint(
            args.checkpoint,
            {
                "job": "support_overnight",
                "seed": args.seed,
                "edits_target": args.edits,
                "last_e": e,
                "best_support": best_s,
                "brent_ok_n": brent_ok_n,
                "tried": tried,
                "improved": improved,
                "equal_keep": equal_keep,
                "accept_rate": (brent_ok_n / tried) if tried else 0.0,
                "resume_from_e": e + 1,
                "out": str(args.out),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    cur = deepcopy(best)
    for e in range(start_e, args.edits + 1):
        erng = random.Random(args.seed * 1_000_003 + e)
        tried += 1
        pos = positions(*mats(cur))
        if len(pos) < 2:
            break
        k = 3 if (len(pos) >= 3 and erng.random() < args.p3) else 2
        k = min(k, len(pos))
        chosen = erng.sample(pos, k)
        olds = []
        for name, t, i in chosen:
            olds.append((name, t, i, getv(cur, name, t, i)))
            setv(cur, name, t, i, erng.choice([0, 1, -1]))
        if brent_ok(*mats(cur)):
            brent_ok_n += 1
            s = support(*mats(cur))
            if s < best_s:
                improved += 1
                log(
                    f"IMPROVED e={e} k={k} support {best_s} -> {s} "
                    f"accept_rate={brent_ok_n/tried:.4f}"
                )
                best_s = s
                best = deepcopy(cur)
                write_out(
                    args.out,
                    best,
                    {"note": f"k={k} edit={e}", "improved": True, "edit": e},
                )
                save_ck(e)
                if best_s <= 151:
                    log(f"HIT TARGET support={best_s}")
            elif s == best_s and erng.random() < 0.01:
                equal_keep += 1
                best = deepcopy(cur)
            else:
                # diversify walk: keep Brent-ok even if worse sometimes
                if s > best_s and erng.random() < 0.002:
                    pass  # stay on worse temporarily
                else:
                    cur = deepcopy(best)
        else:
            for name, t, i, old in olds:
                setv(cur, name, t, i, old)
            cur = deepcopy(best)

        now = time.time()
        if e % args.status_every == 0 or (now - last_ck) >= args.checkpoint_secs:
            elapsed = now - t0
            rate = brent_ok_n / tried if tried else 0.0
            log(
                f"status e={e} best_support={best_s} tried={tried} "
                f"brent_ok={brent_ok_n} accept_rate={rate:.4f} "
                f"improved={improved} equal_keep={equal_keep} "
                f"elapsed_s={elapsed:.1f}"
            )
            save_ck(e)
            last_ck = now

    elapsed = time.time() - t0
    rate = brent_ok_n / tried if tried else 0.0
    log(
        f"done best_support={best_s} tried={tried} brent_ok={brent_ok_n} "
        f"accept_rate={rate:.4f} improved={improved} elapsed_s={elapsed:.1f}"
    )
    write_out(
        args.out,
        best,
        {"note": "final", "improved": best_s < 152, "accept_rate": rate},
    )
    save_ck(args.edits)
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
