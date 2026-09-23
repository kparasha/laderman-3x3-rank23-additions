# Progress snapshot — matrix-multiplication-tensor-3x3

**Date:** 2026-09-23  
**Branch:** `hills/matrix-multiplication-tensor-3x3`  
**Scoreboard (unchanged):** additions **56** · support **152** · rank **23**

## Problem

Find a better-than-known decomposition of the 3×3 matrix-multiplication tensor:
or a **rank &lt; 23** scheme, or (at rank 23) **certified SLP additions &lt; 56**, or **support &lt; 152**.

Why it matters: matrix multiplication sits under scientific computing, ML, and complexity theory. Even tiny exact improvements on 3×3 have been open for decades and can seed asymptotic algorithms.

## What we ran

| Layer | Role |
|-------|------|
| Autolab / Hills climb | Official eval targets |
| Pure-Python `research_director.py` | Fixed `strategies.json` queue — **exhausted** (20 retired) |
| Cursor SDK `agentic_director.py` | Local agent invents tools + hypotheses from the ledger |
| LaunchAgents + `director_dashboard.py` | KeepAlive overnight + localhost status |

Approximate agentic ledger (finished cycles, excluding unit-test): **~48 sterile**, **~11 crashed/timeout**, **0 progress** (no threshold beat). Sterile arches skewed additions-heavy then opportunistic support/rank.

## What we learned (sterile ≠ empty)

- Sun W nullspace is trivial given U,V — W-only CSE cannot unlock &lt;56.
- Large UV-affine / signflip / Stapleton k-edit neighborhoods plateau (adds ≥56, support 152).
- Many “different” CSE schedules share the same expanded gold as Sun56@56 — local hills stay in that component.
- Rank probes (Q-redundancy, pair/triple drop, GF(2)/GF(p)) did not yield exact rank 22.
- Cross-scheme grafts often break Brent; survivors rarely beat CSE baselines.
- Infra lesson: Cursor-shell `nohup` gets reaped; LaunchAgents survive. Caffeinate is optional wake-lock only.

## Next

Switch overnight climb to **Python agentic director** (no Cursor SDK): same ledger/learnings loop, rule-based opportunistic tool selection from `tools/`, network-free.
