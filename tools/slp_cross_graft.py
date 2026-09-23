#!/usr/bin/env python3
"""Cross-graft one product between Sun56 and Stapleton60; solve W; score CSE.

Random UV affine on Sun found no cost<=56. This tries structured hybrids:
replace one rank-1 term (UV only or full UVW) and re-score multi-seed CSE.

  python3 -u tools/slp_cross_graft.py --cse-seeds 12 \\
      --out submissions/director-agentic-cross-graft
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import (  # noqa: E402
    brent_ok,
    score_uvw,
    solve_w,
    to_int_ternary,
    write_out,
)


def graft_triple(base, donor, t):
    u = [r[:] for r in base["u"]]
    v = [r[:] for r in base["v"]]
    w = [r[:] for r in base["w"]]
    u[t] = donor["u"][t][:]
    v[t] = donor["v"][t][:]
    w[t] = donor["w"][t][:]
    return {"u": u, "v": v, "w": w}


def graft_uv_solve(base, donor, t):
    u = [r[:] for r in base["u"]]
    v = [r[:] for r in base["v"]]
    u[t] = donor["u"][t][:]
    v[t] = donor["v"][t][:]
    W, nfree = solve_w(u, v)
    if W is None:
        return None, nfree
    w = to_int_ternary(W)
    if w is None:
        return None, nfree
    return {"u": u, "v": v, "w": w}, nfree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument(
        "--stapleton", type=Path, default=Path("submissions/stapleton60/solution.json")
    )
    ap.add_argument("--cse-seeds", type=int, default=12)
    ap.add_argument("--log", type=Path, default=Path("logs/cross-graft-director.log"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-cross-graft")
    )
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    sun = json.loads(args.sun.read_text(encoding="utf-8"))
    stap = json.loads(args.stapleton.read_text(encoding="utf-8"))
    assert brent_ok(sun["u"], sun["v"], sun["w"])
    assert brent_ok(stap["u"], stap["v"], stap["w"])
    assert len(sun["u"]) == len(stap["u"]) == 23

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    best_total = 56
    best_pack = None
    best_meta = None
    t0 = time.time()
    scored = 0

    bases = [
        ("stapleton_base", stap, sun),
        ("sun_base", sun, stap),
    ]
    modes = ["full_triple", "uv_solve_w"]

    for base_name, base, donor in bases:
        for t in range(23):
            for mode in modes:
                if mode == "full_triple":
                    data = graft_triple(base, donor, t)
                    nfree = 0
                else:
                    out = graft_uv_solve(base, donor, t)
                    if out[0] is None:
                        continue
                    data, nfree = out
                if not brent_ok(data["u"], data["v"], data["w"]):
                    continue
                tot, sides = score_uvw(
                    data["u"],
                    data["v"],
                    data["w"],
                    args.cse_seeds,
                    seed=9000 + t * 17 + (0 if base_name == "stapleton_base" else 500),
                )
                if sides is None:
                    continue
                scored += 1
                if tot < best_total:
                    best_total = tot
                    best_pack = (data, sides)
                    best_meta = {
                        "base": base_name,
                        "t": t,
                        "mode": mode,
                        "nfree": nfree,
                    }
                    log(
                        f"IMPROVED total={tot} base={base_name} t={t} mode={mode} "
                        f"U={sides and sides.get('U')} ..."
                    )

    elapsed = time.time() - t0
    if best_pack and best_total < 56:
        data, sides = best_pack
        write_out(
            args.out,
            data["u"],
            data["v"],
            data["w"],
            sides,
            {**best_meta, "certified_cost": best_total, "improved": True},
        )

    summary = {
        "best_total": best_total,
        "improved": best_total < 56,
        "scored": scored,
        "trials": 23 * len(bases) * len(modes),
        "elapsed_s": elapsed,
        "best_meta": best_meta,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_total < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
