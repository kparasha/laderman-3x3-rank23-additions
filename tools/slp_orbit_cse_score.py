#!/usr/bin/env python3
"""Score CSE cost on each Brent-ok tensor symmetry orbit member (Sun56)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import score_uvw  # noqa: E402
from support_overnight import orbit_seeds  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cse-seeds", type=int, default=8)
    ap.add_argument("--seed", type=int, default=880001)
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-orbit-cse-score"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    t0 = time.time()
    orb = orbit_seeds(base)
    best = 10**9
    best_tag = None
    rows = []
    for sup, tag, data in orb:
        tot, _ = score_uvw(data["u"], data["v"], data["w"], args.cse_seeds, args.seed)
        if tot is None:
            continue
        rows.append({"tag": tag, "support": sup, "cse_total": tot})
        if tot < best:
            best = tot
            best_tag = tag

    summary = {
        "orbit_size": len(orb),
        "scored": len(rows),
        "best_cse_total": best if rows else None,
        "best_tag": best_tag,
        "improved": best < 56,
        "min3": sorted(rows, key=lambda r: r["cse_total"])[:3],
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
