#!/usr/bin/env python3
"""729-d product fingerprint equality for two rank-23 solutions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import brent_ok  # noqa: E402


def fingerprint(data):
    u, v, w = data["u"], data["v"], data["w"]
    out = []
    for a in range(9):
        for b in range(9):
            for c in range(9):
                out.append(sum(u[t][a] * v[t][b] * w[t][c] for t in range(len(u))))
    return tuple(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--b", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-tensor-fingerprint"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    da = json.loads(args.a.read_text(encoding="utf-8"))
    db = json.loads(args.b.read_text(encoding="utf-8"))
    fa, fb = fingerprint(da), fingerprint(db)
    summary = {
        "a": str(args.a),
        "b": str(args.b),
        "brent_a": brent_ok(da["u"], da["v"], da["w"]),
        "brent_b": brent_ok(db["u"], db["v"], db["w"]),
        "same_tensor": fa == fb,
        "diff_entries": sum(x != y for x, y in zip(fa, fb)),
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
