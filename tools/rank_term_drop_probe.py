#!/usr/bin/env python3
"""Drop each rank-1 term; check Brent-ok rank-22 (exact rank drop)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import brent_ok  # noqa: E402


def drop_term(data, t):
    u = [r[:] for i, r in enumerate(data["u"]) if i != t]
    v = [r[:] for i, r in enumerate(data["v"]) if i != t]
    w = [r[:] for i, r in enumerate(data["w"]) if i != t]
    return {"u": u, "v": v, "w": w}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cse-seeds", type=int, default=4)
    ap.add_argument("--seed", type=int, default=860001)
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-rank-term-drop")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    summary = {"schemes": {}, "rank22_brent": []}

    for name in ("sun56", "stapleton60"):
        p = Path(f"submissions/{name}/solution.json")
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        hits = []
        for t in range(len(data["u"])):
            trial = drop_term(data, t)
            if brent_ok(trial["u"], trial["v"], trial["w"]):
                hits.append(t)
        summary["schemes"][name] = {
            "rank": len(data["u"]),
            "drops_brent_ok": hits,
            "rank22_count": len(hits),
        }
        summary["rank22_brent"].extend((name, t) for t in hits)

    summary["improved"] = len(summary["rank22_brent"]) > 0
    summary["elapsed_s"] = time.time() - t0
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
