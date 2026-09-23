# X / Twitter thread

**Images:** post 1 → `arch_research_loop.png` · post 2 → `arch_sdk_vs_python.png` · post 3 → screenshot of `chart_scoreboard.svg` · post 4 → `chart_outcomes.svg` / `chart_arch_split.svg`

---

**1/**
spent a chunk of this week on a classic open problem that sounds almost joke-sized:

can you do better than the known best for **3×3 matrix multiplication**?

not “faster CUDA.” exact structure. fewer multiplies / fewer adds / sparser factors.

**2/**
why it matters (quick): matmul sits under so much of computing + theory. tiny exact wins on small tensors have a habit of becoming bigger algorithms later.

so yeah — worth losing sleep over.

**3/**
instead of one-off scripts I built an **auto-research loop**:

hypothesize → run a bounded experiment → check the scoreboard → write learnings → pick the next try

two directors:
• Cursor SDK agent that invents tools overnight
• pure **Python** director (no agent API) that just keeps climbing

**4/**
three metrics, any win counts:
• additions &lt; 56
• support &lt; 152
• rank &lt; 23

honest ending: still **56 / 152 / 23**. didn’t solve it.

**5/**
what we *did* get: a map of dead ends.

Sun’s W is locked given U,V. huge edit neighborhoods plateau. a lot of “new” CSE schedules are the same gold as the known 56. rank-drop didn’t hand us 22.

sterile runs still teach you where not to dig.

**6/**
also: if your “overnight” job was started from an IDE agent shell… check that it’s still alive in the morning 🙂

LaunchAgents &gt; vibes.

default climb is moving to the Python director now. SDK stays for invention mode.

open problems people — what’s your favorite “tiny on paper, brutal in practice” climb?
