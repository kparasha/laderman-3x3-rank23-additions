# LinkedIn post

**Images to attach (in order):**
1. `docs/social/arch_research_loop.png` — the auto-research loop
2. `docs/social/arch_sdk_vs_python.png` — SDK director vs Python director
3. `docs/social/chart_scoreboard.svg` — three metrics (open in browser → screenshot, or convert to PNG)
4. `docs/social/chart_outcomes.svg` + `chart_arch_split.svg` — what the overnight runs looked like

---

We’ve all got that one research problem that looks tiny on a whiteboard and somehow eats a whole week.

Mine this round: **3×3 matrix multiplication**.

Not “make matmul faster on a GPU.” The old-school exact question:

> Can you multiply 3×3 matrices with fewer than the usual number of multiplications — or, at the known best rank (23), make the *addition* circuit smaller / the factorization *sparser*?

Why bother? Matrix multiplication is under basically everything — scientific computing, ML kernels, complexity theory. Even a tiny exact improvement on 3×3 has been open for decades, and historically these local wins seed better asymptotic algorithms. So it’s not trivia. It’s a clean “prove you can push a frontier” problem.

**What I actually built** wasn’t another hand-tuned script. It was an **auto-research loop**:

hypothesis → bounded experiment → scoreboard check → write it down in a ledger + learnings file → pick the next move.

I ran two flavors of “director”:

1. **Cursor SDK agentic director** — a local coding agent that could invent new tools overnight, read the ledger, and try not to repeat sterile neighborhoods.
2. **Pure Python agentic director** — same loop, no cloud agent API: it discovers tools in `tools/`, opportunistically chooses among three metrics, and runs smoke-scale experiments as subprocesses. Lighter, network-free, easier to leave running.

**The three scoreboard metrics** (any win counts; cross-pollination encouraged):

- certified SLP **additions &lt; 56** (at rank 23)
- **support &lt; 152**
- **rank &lt; 23**

Honest scoreboard after a lot of overnight cycles: still **56 / 152 / 23**. We didn’t crack it.

But sterile ≠ useless. The machine (and I) learned a pile of “don’t bother re-running this” facts: Sun’s W is locked once U,V are fixed; big UV / signflip / Stapleton edit neighborhoods plateau; a lot of fancy CSE schedules secretly share the same expanded “gold” as the known 56; rank-drop probes didn’t hand us a clean 22. Also an infra lesson: if you `nohup` from an IDE agent shell, your “overnight” job may quietly die. LaunchAgents fixed that.

I’m switching the default overnight climb to the **Python director** now — keep the SDK path around when I want tool invention, but let the dumb-reliable loop grind without API keys.

If you’re into open problems, Autolab/Hills-style climbs, or “agentic research that still has to face a scoreboard,” happy to compare notes.

#OpenProblems #MatrixMultiplication #AgenticAI #ResearchEngineering #Python
