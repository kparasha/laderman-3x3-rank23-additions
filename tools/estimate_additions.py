#!/usr/bin/env python3
"""Greedy CSE on expanded linear forms to estimate addition counts for a UVW scheme.

Unofficial diagnostic: not a hills metric. Counts binary +/− needed to form each
U/V row from A/B entries and each C coordinate from products (no shared CSE across
rows beyond a simple greedy common-subexpression pass on the multiset of forms).
"""

from __future__ import annotations

import json
import sys
from collections import Counter


def form_cost(coeffs):
    """Additions to form sum c_i x_i with c in {-1,0,1,...} treating |c|>1 as repeats."""
    terms = 0
    for c in coeffs:
        terms += abs(c)
    return max(terms - 1, 0)


def greedy_cse_cost(rows):
    """Very rough CSE: repeatedly extract the most common 2-sparse ± pattern among remaining rows."""
    # Represent each row as frozenset of (index, sign) for nonzero unit coeffs; scale abs>1 not handled optimally
    forms = []
    for row in rows:
        terms = []
        for i, c in enumerate(row):
            if c == 0:
                continue
            sign = 1 if c > 0 else -1
            for _ in range(abs(c)):
                terms.append((i, sign))
        forms.append(terms)
    # Without deep CSE, cost is sum(max(len(terms)-1,0))
    base = sum(max(len(t) - 1, 0) for t in forms)
    # Count shared identical pairs of terms appearing in multiple forms
    pair_counts = Counter()
    for terms in forms:
        seen = set()
        for a in range(len(terms)):
            for b in range(a + 1, len(terms)):
                pair = tuple(sorted([terms[a], terms[b]]))
                if pair not in seen:
                    pair_counts[pair] += 1
                    seen.add(pair)
    # Each pair that appears k>1 times can save (k-1) additions if extracted once
    savings = sum(k - 1 for k, in ((v,) for v in pair_counts.values()) if False)
    savings = sum(v - 1 for v in pair_counts.values() if v > 1)
    # Cap savings so cost stays non-negative
    return max(base - min(savings, base), 0), base, savings


def main():
    data = json.loads(open(sys.argv[1], encoding="utf-8").read())
    u, v, w = data["u"], data["v"], data["w"]
    u_cse, u_base, u_sav = greedy_cse_cost(u)
    v_cse, v_base, v_sav = greedy_cse_cost(v)
    w_cse, w_base, w_sav = greedy_cse_cost(w)
    print(
        json.dumps(
            {
                "U": {"naive": u_base, "cse_est": u_cse, "pair_savings": u_sav},
                "V": {"naive": v_base, "cse_est": v_cse, "pair_savings": v_sav},
                "W": {"naive": w_base, "cse_est": w_cse, "pair_savings": w_sav},
                "total_naive": u_base + v_base + w_base,
                "total_cse_est": u_cse + v_cse + w_cse,
                "note": "unofficial addition estimate; Sun56 SLP remains the certified 56",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
