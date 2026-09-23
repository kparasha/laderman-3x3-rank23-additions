#!/usr/bin/env python3
"""If two rank-1 terms are identical (canon), dropping one may yield Brent rank 22."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from support_overnight import brent_ok  # noqa: E402


def term_key(u, v, w, t):
    a, b, c = tuple(u[t]), tuple(v[t]), tuple(w[t])
    na, nb, nc = tuple(-x for x in a), tuple(-x for x in b), tuple(-x for x in c)
    return min((a, b, c), (na, nb, nc))


def drop_one(data, t):
    d = deepcopy(data)
    for name in ("u", "v", "w"):
        d[name] = [row for i, row in enumerate(d[name]) if i != t]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-dup-term"))
    args = ap.parse_args()
    data = json.loads(args.src.read_text(encoding="utf-8"))
    u, v, w = data["u"], data["v"], data["w"]
    keys = [term_key(u, v, w, t) for t in range(len(u))]
    ctr = Counter(keys)
    dups = [k for k, c in ctr.items() if c > 1]
    hits = []
    for t in range(len(u)):
        if ctr[keys[t]] < 2:
            continue
        d2 = drop_one(data, t)
        hits.append({"drop": t, "rank": len(d2["u"]), "brent": brent_ok(*[d2[n] for n in ("u", "v", "w")])})
    best_rank = 23 if not any(h["brent"] for h in hits) else 22
    summary = {"duplicates": len(dups), "drop_trials": len(hits), "hits": hits, "best_rank": best_rank}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))
    return 0 if best_rank < 23 else 1


if __name__ == "__main__":
    raise SystemExit(main())
