#!/usr/bin/env python3
"""Compare Sun SIDES0@56 vs CSE-hill@62 expanded UVW; bounded rebuild if they differ.

  python3 -u tools/slp_sun_uvw_equivalence.py --rebuild-seeds 20
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_addition_search import (  # noqa: E402
    SIDES0,
    brent_ok,
    rebuild_sides_from_uvw,
    sun_uvw_hill,
    total_cost,
)
from slp_w_mutate import cost  # noqa: E402


def term_key(u, v, w, t):
    a = tuple(u[t])
    b = tuple(v[t])
    c = tuple(w[t])
    na = tuple(-x for x in a)
    nb = tuple(-x for x in b)
    nc = tuple(-x for x in c)
    k1 = (a, b, c)
    k2 = (na, nb, nc)
    return min(k1, k2)


def multiset_uvw(u, v, w):
    return tuple(sorted(term_key(u, v, w, t) for t in range(len(u))))


def sides_uvw(sides_path: Path):
    sides = json.loads(sides_path.read_text(encoding="utf-8"))
    u, v, w = sun_uvw_hill(sides)
    return u, v, w, total_cost(sides)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides56", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument(
        "--sides62",
        type=Path,
        default=Path("submissions/director-agentic-sun-cse-hill/sides.json"),
    )
    ap.add_argument("--rebuild-seeds", type=int, default=20)
    ap.add_argument("--seed-base", type=int, default=670001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun-uvw-equiv"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun-uvw-equiv-cycle67.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    u56, v56, w56, c56 = sides_uvw(args.sides56)
    u62, v62, w62, c62 = sides_uvw(args.sides62)
    m56 = multiset_uvw(u56, v56, w56)
    m62 = multiset_uvw(u62, v62, w62)
    same_multiset = m56 == m62
    same_ordered = (u56, v56, w56) == (u62, v62, w62)
    log(
        f"cost56={c56} cost62={c62} same_ordered={same_ordered} "
        f"same_multiset={same_multiset}"
    )

    best_total = min(c56, c62)
    best_meta = {"source": "certificates"}
    if not same_multiset:
        for s in range(args.rebuild_seeds):
            for label, (uu, vv, ww) in (
                ("from56", (u56, v56, w56)),
                ("from62", (u62, v62, w62)),
            ):
                sides = rebuild_sides_from_uvw(uu, vv, ww, seed=args.seed_base + s)
                if sides is None:
                    continue
                tot = total_cost(sides)
                if tot < best_total:
                    best_total = tot
                    best_meta = {"rebuild": label, "seed": s, "total": tot}
                    log(f"IMPROVED {label} seed={s} total={tot}")

    improved = best_total < 56
    summary = {
        "cert_total56": c56,
        "cert_total62": c62,
        "same_ordered_uvw": same_ordered,
        "same_multiset_uvw": same_multiset,
        "rebuild_seeds": args.rebuild_seeds,
        "best_total": best_total,
        "improved": improved,
        "best_meta": best_meta,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if improved else 1


if __name__ == "__main__":
    raise SystemExit(main())
