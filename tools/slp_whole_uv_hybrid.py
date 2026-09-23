#!/usr/bin/env python3
"""All 3×3 cross-scheme (U,V) pairs from Sun/Stapleton/Perminov; solve W; CSE score.

Single- and two-product grafts failed. Whole-matrix mixes may land in a new
Brent rank-23 factorization with certified SLP <56.

  python3 -u tools/slp_whole_uv_hybrid.py --cse-seeds 14
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

from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary, write_out  # noqa: E402


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cse-seeds", type=int, default=14)
    ap.add_argument("--seed", type=int, default=420042)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-whole-uv-hybrid"))
    ap.add_argument("--log", type=Path, default=Path("logs/whole-uv-hybrid-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    schemes = {
        "sun": load(Path("submissions/sun56/solution.json")),
        "stap": load(Path("submissions/stapleton60/solution.json")),
        "perm": load(Path("submissions/perminov58/solution.json")),
    }

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start schemes={list(schemes)} cse_seeds={args.cse_seeds}")
    t0 = time.time()
    best_total = 10**9
    best_pack = None
    best_meta = None
    brent_n = scored = 0
    trial = 0

    for uname, udata in schemes.items():
        for vname, vdata in schemes.items():
            u = [r[:] for r in udata["u"]]
            v = [r[:] for r in vdata["v"]]
            W, nfree = solve_w(u, v)
            if W is None:
                log(f"skip u={uname} v={vname} solve_fail")
                continue
            w = to_int_ternary(W)
            if w is None:
                log(f"skip u={uname} v={vname} nonternary")
                continue
            data = {"u": u, "v": v, "w": w}
            if not brent_ok(u, v, w):
                log(f"skip u={uname} v={vname} brent_fail")
                continue
            brent_n += 1
            tot, sides = score_uvw(u, v, w, args.cse_seeds, args.seed + trial * 31)
            trial += 1
            if sides is None:
                continue
            scored += 1
            log(f"scored u={uname} v={vname} total={tot} nfree={nfree}")
            if tot < best_total:
                best_total = tot
                best_pack = (data, sides)
                best_meta = {"u_scheme": uname, "v_scheme": vname, "nfree": nfree}

    elapsed = time.time() - t0
    improved = best_pack is not None and best_total < 56
    if improved and best_pack:
        data, sides = best_pack
        write_out(
            args.out,
            data["u"],
            data["v"],
            data["w"],
            sides,
            {**best_meta, "improved": True, "certified_cost": best_total},
        )

    summary = {
        "trials": trial,
        "brent_ok": brent_n,
        "scored": scored,
        "best_total": best_total if best_pack else None,
        "improved": improved,
        "best_meta": best_meta,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if improved else 1


if __name__ == "__main__":
    raise SystemExit(main())
