#!/usr/bin/env python3
"""Bounded overnight mutation search on Sun's W SLP (U/V fixed at 13).

Target: certified W cost 30 → 29 (total 56 → 55), rank 23, Brent = 0.

Strategy (cheap, not quadratic rebuild):
  - Freeze Sun U/V SLPs and the expanded W column targets.
  - Mutate only the W SLP schedule:
      1) extract a common ±pair shared by ≥2 finals (net save ≥1)
      2) rewrite one final to a shorter expression over current vectors
      3) drop an unused intermediate / compact indices
      4) add one intermediate that shortens ≥2 finals
  - Accept only if expand(W) matches the gold targets exactly.
  - Total certified cost = cost(U)+cost(V)+cost(W) with Sun's cost model.

Usage:
  python3 -u tools/slp_w_mutate.py --rounds 200000 --seed 0 \\
      --log logs/w-mutate.log --out submissions/attempt016-w-mutate

Safe to leave overnight; writes best certificate whenever it improves.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from copy import deepcopy
from itertools import combinations
from pathlib import Path

# Sun SIDES (from verify.py) — U/V stay frozen
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
        if a >= len(vs) or b >= len(vs):
            raise IndexError("bad intermediate index")
        va, vb = vs[a], vs[b]
        vs.append(tuple(va[i] + s * vb[i] for i in range(n)))
    out = []
    for f in side["final"]:
        acc = [0] * n
        for idx, c in f:
            if idx >= len(vs):
                raise IndexError("bad final index")
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


def matches_gold(side, gold) -> bool:
    try:
        out, _ = expand(side)
    except Exception:
        return False
    return out == list(gold)


def normalize_final(f):
    """Merge duplicate indices; drop zeros."""
    acc = {}
    for idx, c in f:
        acc[idx] = acc.get(idx, 0) + c
    return [(i, c) for i, c in sorted(acc.items()) if c != 0]


def referenced_indices(side):
    used = set()
    for a, s, b in side["inter"]:
        used.add(a)
        used.add(b)
    for f in side["final"]:
        for idx, _ in f:
            used.add(idx)
    # intermediates also referenced by later inters — already covered
    return used


def compact_side(side):
    """Drop unused intermediates and renumber (keep base 0..base_dim-1)."""
    base = side["base_dim"]
    n_total = base + len(side["inter"])
    # Which intermediate slots (base..n_total-1) are needed?
    # Build dependency: start from finals, walk inter defs backward.
    needed = set()
    for f in side["final"]:
        for idx, _ in f:
            needed.add(idx)
    changed = True
    while changed:
        changed = False
        for k, (a, s, b) in enumerate(side["inter"]):
            idx = base + k
            if idx in needed:
                if a not in needed:
                    needed.add(a)
                    changed = True
                if b not in needed:
                    needed.add(b)
                    changed = True
    # Keep all base; keep needed inters in order
    keep_inter = []
    old_to_new = {i: i for i in range(base)}
    for k, trip in enumerate(side["inter"]):
        idx = base + k
        if idx in needed:
            old_to_new[idx] = base + len(keep_inter)
            keep_inter.append(trip)
    # Remap trips and finals
    new_inter = []
    for a, s, b in keep_inter:
        if a not in old_to_new or b not in old_to_new:
            return None
        new_inter.append((old_to_new[a], s, old_to_new[b]))
    new_finals = []
    for f in side["final"]:
        nf = []
        for idx, c in f:
            if idx not in old_to_new:
                return None
            nf.append((old_to_new[idx], c))
        new_finals.append(normalize_final(nf))
    return {"base_dim": base, "inter": new_inter, "final": new_finals}


def try_extract_common_pair(side, rng):
    """Extract a ±pair used in ≥2 finals into one intermediate."""
    s = deepcopy(side)
    # Collect pairs per final (unordered by sorted index, track signs relative)
    pair_locations = {}  # key -> list of (final_i, i_pos, j_pos, sa, sb)
    for fi, f in enumerate(s["final"]):
        if len(f) < 2:
            continue
        for (i, ci), (j, cj) in combinations(f, 2):
            if i == j:
                continue
            # normalize order by index
            if i < j:
                key = (i, j, ci, cj)
                loc = (fi, i, j, ci, cj)
            else:
                key = (j, i, cj, ci)
                loc = (fi, j, i, cj, ci)
            pair_locations.setdefault(key, []).append(loc)

    candidates = [k for k, locs in pair_locations.items() if len(locs) >= 2]
    if not candidates:
        return None
    rng.shuffle(candidates)
    for key in candidates[:20]:
        locs = pair_locations[key]
        i, j, ci, cj = key
        # New vector should be ci*vs[i] + cj*vs[j]; as SLP inter we only have
        # vs[a] + s*vs[b]. Factor signs into the final reference.
        # Write inter as (i, sign, j) representing vs[i] + sign*vs[j], then
        # scale in the final. Need ci*i + cj*j = scale * (i + s*j).
        # Cases:
        #   scale=ci, s such that scale*s = cj => s = cj/ci if |ci|=|cj|=1
        if abs(ci) != 1 or abs(cj) != 1:
            continue
        # inter: vs[i] + s*vs[j] with s = cj/ci (since both ±1)
        s_inter = cj // ci  # ±1
        trial = deepcopy(s)
        new_idx = trial["base_dim"] + len(trial["inter"])
        trial["inter"].append((i, s_inter, j))
        # Replace the pair in each listed final with (new_idx, ci)
        for fi, ii, jj, sai, saj in locs:
            f = trial["final"][fi]
            # remove one occurrence of (ii,sai) and (jj,saj)
            nf = []
            removed_i = removed_j = False
            for idx, c in f:
                if not removed_i and idx == ii and c == sai:
                    removed_i = True
                    continue
                if not removed_j and idx == jj and c == saj:
                    removed_j = True
                    continue
                nf.append((idx, c))
            if not (removed_i and removed_j):
                break
            nf.append((new_idx, sai))  # sai == ci from key normalization
            trial["final"][fi] = normalize_final(nf)
        else:
            trial = compact_side(trial) or trial
            return trial
    return None


def try_shorten_one_final(side, gold, rng, vs=None):
    """Rewrite one multi-term final using a random 1- or 2-term combo of current vs."""
    s = deepcopy(side)
    if vs is None:
        _, vs = expand(s)
    multi = [fi for fi, f in enumerate(s["final"]) if len(f) >= 2]
    if not multi:
        return None
    fi = rng.choice(multi)
    target = gold[fi]
    dim = len(target)
    n = len(vs)

    # Try random single matches already handled by extract; try random pairs
    tries = min(800, n * n)
    for _ in range(tries):
        i = rng.randrange(n)
        j = rng.randrange(n)
        if i == j:
            for sa in (1, -1):
                g = tuple(sa * vs[i][k] for k in range(dim))
                if g == target:
                    s2 = deepcopy(s)
                    s2["final"][fi] = [(i, sa)]
                    return s2
            continue
        for sa in (1, -1):
            for sb in (1, -1):
                g = tuple(sa * vs[i][k] + sb * vs[j][k] for k in range(dim))
                if g == target:
                    s2 = deepcopy(s)
                    s2["final"][fi] = normalize_final([(i, sa), (j, sb)])
                    return s2
    # Try 3-term only if final currently longer than 3
    if len(s["final"][fi]) >= 4:
        for _ in range(400):
            i, j, k = rng.sample(range(n), 3)
            for sa in (1, -1):
                for sb in (1, -1):
                    for sc in (1, -1):
                        g = tuple(
                            sa * vs[i][t] + sb * vs[j][t] + sc * vs[k][t]
                            for t in range(dim)
                        )
                        if g == target:
                            s2 = deepcopy(s)
                            s2["final"][fi] = normalize_final(
                                [(i, sa), (j, sb), (k, sc)]
                            )
                            return s2
    return None


def try_add_inter_shorten_two(side, gold, rng):
    """Add vs[a]+s*vs[b]; if ≥2 finals become expressible shorter, keep."""
    s = deepcopy(side)
    _, vs = expand(s)
    n = len(vs)
    if n < 2:
        return None
    a = rng.randrange(n)
    b = rng.randrange(n)
    if a == b:
        return None
    sign = rng.choice([1, -1])
    trial = deepcopy(s)
    new_idx = trial["base_dim"] + len(trial["inter"])
    trial["inter"].append((a, sign, b))
    _, vs2 = expand(trial)
    # For each final, see if we can rewrite shorter using new vector
    improved = 0
    new_finals = []
    dim = len(gold[0])
    for fi, f in enumerate(trial["final"]):
        target = gold[fi]
        old_len = len(f)
        # single involving new
        found = None
        vnew = vs2[new_idx]
        if vnew == target:
            found = [(new_idx, 1)]
        elif tuple(-x for x in vnew) == target:
            found = [(new_idx, -1)]
        else:
            # two-term including new
            for i in range(len(vs2)):
                if i == new_idx:
                    continue
                for sa in (1, -1):
                    for sb in (1, -1):
                        g = tuple(sa * vnew[k] + sb * vs2[i][k] for k in range(dim))
                        if g == target:
                            found = [(new_idx, sa), (i, sb)]
                            break
                    if found:
                        break
                if found:
                    break
        if found and len(found) < old_len:
            new_finals.append(normalize_final(found))
            improved += 1
        else:
            new_finals.append(f)
    if improved < 2:
        return None
    trial["final"] = new_finals
    trial = compact_side(trial) or trial
    return trial


def try_drop_random_inter(side, gold, rng):
    """Delete one intermediate and hope finals still match after compact fails → reject."""
    if not side["inter"]:
        return None
    s = deepcopy(side)
    k = rng.randrange(len(s["inter"]))
    base = s["base_dim"]
    drop_idx = base + k
    # Remove inter k; remap indices > drop_idx
    new_inter = []
    for t, (a, sgn, b) in enumerate(s["inter"]):
        if t == k:
            continue
        def map_i(x):
            if x == drop_idx:
                return None
            if x > drop_idx:
                return x - 1
            return x
        a2, b2 = map_i(a), map_i(b)
        if a2 is None or b2 is None:
            return None  # depended on dropped
        new_inter.append((a2, sgn, b2))
    new_finals = []
    for f in s["final"]:
        nf = []
        for idx, c in f:
            if idx == drop_idx:
                return None
            nf.append((idx - 1 if idx > drop_idx else idx, c))
        new_finals.append(normalize_final(nf))
    trial = {"base_dim": base, "inter": new_inter, "final": new_finals}
    return trial


def mutate(side, gold, rng):
    op = rng.choices(
        ["common_pair", "shorten_final", "add_inter", "drop_inter"],
        weights=[5, 3, 3, 1],
        k=1,
    )[0]
    if op == "common_pair":
        return try_extract_common_pair(side, rng), op
    if op == "shorten_final":
        return try_shorten_one_final(side, gold, rng), op
    if op == "add_inter":
        return try_add_inter_shorten_two(side, gold, rng), op
    return try_drop_random_inter(side, gold, rng), op


def write_best(out_dir: Path, w_side, u_side, v_side, meta: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    u, v, w = sun_uvw_hill(u_side, v_side, w_side)
    (out_dir / "solution.json").write_text(
        json.dumps({"u": u, "v": v, "w": w}, separators=(",", ":")), encoding="utf-8"
    )
    sides = {"U": u_side, "V": v_side, "W": w_side}
    (out_dir / "sides.json").write_text(json.dumps(sides, indent=2), encoding="utf-8")
    cert = {
        **meta,
        "brent_ok": brent_ok(u, v, w),
        "rank": 23,
        "support": sum(x != 0 for M in (u, v, w) for row in M for x in row),
        "breakdown": {
            "U": cost(u_side),
            "V": cost(v_side),
            "W": cost(w_side),
        },
        "certified_cost": cost(u_side) + cost(v_side) + cost(w_side),
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
    ap.add_argument("--rounds", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--log", type=Path, default=Path("logs/w-mutate.log"))
    ap.add_argument("--out", type=Path, default=Path("submissions/attempt016-w-mutate"))
    ap.add_argument("--status-every", type=int, default=2000)
    ap.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("logs/checkpoints/mutate_checkpoint.json"),
    )
    ap.add_argument("--resume", type=Path, default=None)
    ap.add_argument("--start-r", type=int, default=1)
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)

    start_r = args.start_r
    if args.resume and args.resume.exists():
        ck = json.loads(args.resume.read_text(encoding="utf-8"))
        start_r = int(ck.get("resume_from_r") or (int(ck.get("last_r", 0)) + 1))
        if "seed" in ck:
            args.seed = int(ck["seed"])
        if "rounds_target" in ck and args.rounds == 200_000:
            args.rounds = int(ck["rounds_target"])

    u_side = deepcopy(SIDES0["U"])
    v_side = deepcopy(SIDES0["V"])
    w_side = deepcopy(SIDES0["W"])
    gold_w, _ = expand(w_side)
    assert matches_gold(w_side, gold_w)

    best = deepcopy(w_side)
    best_c = cost(best)
    base_uv = cost(u_side) + cost(v_side)
    assert base_uv == 26

    # Restore best W SLP from out if present
    sides_path = args.out / "sides.json"
    if sides_path.exists():
        try:
            sides = json.loads(sides_path.read_text(encoding="utf-8"))
            if "W" in sides and matches_gold(sides["W"], gold_w):
                best = sides["W"]
                best_c = cost(best)
        except Exception:
            pass

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def save_ck(r, accepted, improved, elapsed):
        atomic_checkpoint(
            args.checkpoint,
            {
                "job": "slp_w_mutate",
                "seed": args.seed,
                "rounds_target": args.rounds,
                "last_r": r,
                "best_W": best_c,
                "best_total": base_uv + best_c,
                "accepted": accepted,
                "improved": improved,
                "elapsed_s": elapsed,
                "resume_from_r": r + 1,
                "out": str(args.out),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    log(
        f"start W={best_c} total={base_uv + best_c} "
        f"target W<=29 total<=55 rounds={args.rounds} seed={args.seed} "
        f"start_r={start_r}"
    )
    if start_r == 1:
        write_best(
            args.out,
            best,
            u_side,
            v_side,
            {"note": "baseline Sun W SLP", "improved": False, "baseline_W": 30},
        )

    accepted = 0
    improved = 0
    t0 = time.time()
    for r in range(start_r, args.rounds + 1):
        # Per-round RNG so --resume is exact (independent of prior rounds).
        rng = random.Random(args.seed * 1_000_003 + r)
        cand, op = mutate(best, gold_w, rng)
        if cand is None:
            if r % args.status_every == 0:
                elapsed = time.time() - t0
                log(
                    f"status r={r} best_W={best_c} total={base_uv + best_c} "
                    f"accepted={accepted} improved={improved} "
                    f"elapsed_s={elapsed:.1f}"
                )
                save_ck(r, accepted, improved, elapsed)
            continue
        if not matches_gold(cand, gold_w):
            continue
        accepted += 1
        c = cost(cand)
        # Keep equal-cost diversify sometimes; always keep improvements
        if c < best_c or (c == best_c and rng.random() < 0.02):
            if c < best_c:
                improved += 1
                log(
                    f"IMPROVED r={r} op={op} W {best_c} -> {c} "
                    f"total {base_uv + best_c} -> {base_uv + c}"
                )
                best_c = c
                best = cand
                cert = write_best(
                    args.out,
                    best,
                    u_side,
                    v_side,
                    {
                        "note": f"mutation op={op} at round {r}",
                        "improved": best_c < 30,
                        "baseline_W": 30,
                        "round": r,
                    },
                )
                # Full Brent check on keepers
                if not cert["brent_ok"]:
                    log("ERROR brent failed on keeper — aborting")
                    return 2
                if best_c <= 29:
                    log(f"HIT TARGET W={best_c} total={base_uv + best_c}")
                    save_ck(r, accepted, improved, time.time() - t0)
                    return 0
            else:
                best = cand  # diversify at same cost

        if r % args.status_every == 0:
            elapsed = time.time() - t0
            log(
                f"status r={r} best_W={best_c} total={base_uv + best_c} "
                f"accepted={accepted} improved={improved} "
                f"elapsed_s={elapsed:.1f}"
            )
            save_ck(r, accepted, improved, elapsed)

    elapsed = time.time() - t0
    log(
        f"done best_W={best_c} total={base_uv + best_c} "
        f"accepted={accepted} improved={improved} elapsed_s={elapsed:.1f}"
    )
    save_ck(args.rounds, accepted, improved, elapsed)
    return 0 if best_c < 30 else 1


if __name__ == "__main__":
    raise SystemExit(main())
