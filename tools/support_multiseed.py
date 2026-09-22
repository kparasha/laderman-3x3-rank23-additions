#!/usr/bin/env python3
"""Support search across multiple seed schemes + multi-seed 2/3/4-edits.

  python3 -u tools/support_multiseed.py submissions/director-sup-multi 111 80000
"""

from __future__ import annotations

import json
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

SEEDS = [
    Path("submissions/stapleton60/solution.json"),
    Path("submissions/smoke-baseline/solution.json"),  # Laderman-ish
    Path("submissions/sun56/solution.json"),
    Path("submissions/perminov58/solution.json"),
]


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


def support(u, v, w) -> int:
    return sum(x != 0 for M in (u, v, w) for row in M for x in row)


def mats(d):
    return d["u"], d["v"], d["w"]


def positions(d):
    out = []
    for name in ("u", "v", "w"):
        for t, row in enumerate(d[name]):
            for i, x in enumerate(row):
                if x != 0:
                    out.append((name, t, i))
    return out


def exhaustive_zero(best):
    cur = deepcopy(best)
    best_s = support(*mats(best))
    changed = True
    while changed:
        changed = False
        for name, t, i in positions(cur):
            old = cur[name][t][i]
            cur[name][t][i] = 0
            if brent_ok(*mats(cur)):
                s = support(*mats(cur))
                if s < best_s:
                    best, best_s, changed = deepcopy(cur), s, True
                    break
            cur[name][t][i] = old
        cur = deepcopy(best)
    return best, best_s


def main():
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    edits = int(sys.argv[3]) if len(sys.argv) > 3 else 50000
    rng = random.Random(seed)
    best = None
    best_s = 10**9
    best_src = None
    t0 = time.time()

    for src in SEEDS:
        if not src.exists():
            continue
        data = json.loads(src.read_text(encoding="utf-8"))
        if not brent_ok(*mats(data)):
            print(f"skip bad brent {src}", flush=True)
            continue
        data, s0 = exhaustive_zero(data)
        print(f"seed {src} after-zero support={s0}", flush=True)
        if s0 < best_s:
            best, best_s, best_src = deepcopy(data), s0, str(src)

    if best is None:
        print("no valid seeds")
        return 2

    improved = 0
    brent_ok_n = 0
    cur = deepcopy(best)
    for e in range(1, edits + 1):
        erng = random.Random(seed * 1_000_003 + e)
        pos = positions(cur)
        if len(pos) < 2:
            break
        k = erng.choices([2, 3, 4], weights=[5, 3, 1], k=1)[0]
        k = min(k, len(pos))
        chosen = erng.sample(pos, k)
        olds = [(n, t, i, cur[n][t][i]) for n, t, i in chosen]
        for n, t, i in chosen:
            cur[n][t][i] = erng.choice([0, 1, -1])
        if brent_ok(*mats(cur)):
            brent_ok_n += 1
            s = support(*mats(cur))
            if s < best_s:
                improved += 1
                print(f"IMPROVED e={e} k={k} {best_s} -> {s} src={best_src}", flush=True)
                best_s, best = s, deepcopy(cur)
            elif s == best_s and erng.random() < 0.01:
                best = deepcopy(cur)
            elif s > best_s and erng.random() < 0.001:
                pass
            else:
                cur = deepcopy(best)
        else:
            for n, t, i, old in olds:
                cur[n][t][i] = old
            cur = deepcopy(best)
        if e % max(5000, edits // 10) == 0:
            print(
                f"status e={e} best={best_s} improved={improved} "
                f"accept={brent_ok_n/e:.4f} elapsed_s={time.time()-t0:.1f}",
                flush=True,
            )

    out.mkdir(parents=True, exist_ok=True)
    (out / "solution.json").write_text(
        json.dumps(best, separators=(",", ":")), encoding="utf-8"
    )
    cert = {
        "best_support": best_s,
        "improved": improved > 0 or best_s < 152,
        "improvements": improved,
        "from_src": best_src,
        "brent_ok": brent_ok(*mats(best)),
        "rank": len(best["u"]),
        "support": best_s,
    }
    (out / "support_certificate.json").write_text(json.dumps(cert, indent=2), encoding="utf-8")
    print(f"done best_support={best_s} improved={improved} wrote {out}", flush=True)
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
