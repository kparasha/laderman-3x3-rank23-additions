#!/usr/bin/env python3
"""Product-matrix rank over GF(p) for p in {5,7}."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from rank_gf2_probe import product_matrix_mod, rank_mod_p  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-gfp"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in ("sun56", "stapleton60"):
        p = Path(f"submissions/{name}/solution.json")
        data = json.loads(p.read_text(encoding="utf-8"))
        out[name] = {str(pr): rank_mod_p(product_matrix_mod(data, pr), pr) for pr in (5, 7)}
    summary = {"ranks": out, "any_lt23": any(r < 23 for d in out.values() for r in d.values())}
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["any_lt23"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
