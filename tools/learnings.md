# Research learnings (agentic director)

Hard facts (do not re-run these neighborhoods with the same seeds/moves):

- Sun W nullspace dim=0 given U,V — cannot vary W alone for additions.
- Signflip + greedy W CSE always lands >=57 (improvements=0 overnight).
- UV-affine mutate+solve W: no mass at cost<=56 (scored tens of thousands).
- Stapleton 2/3-edit: accept_rate~8.5% but improved=0 over ~2M edits (plateau at 152).
- Scheme CSE Stapleton/Perminov/Laderman bottoms ~64–66 with le56=0.
- Multi-seed support stuck at 152; flipgraph/rank-drop found no exact rank<23.

Priority: additions (certified SLP <56 @ rank 23) → support <152 → rank <23.

Baselines: Sun56 adds=56, Stapleton support=152, rank=23.

## Updates

(appended by agentic_director after each cycle)

- 2026-09-22 17:40 cycle=100 label=sterile arch=additions metric=56 hyp=unit-test
- 2026-09-22 19:52 cycle=agentic label=sterile arch=support metric=152 hyp=pair-zero-orbit (26 seeds; W beam: Sun W has 0 CSE neighbors)
- 2026-09-22 20:00 cycle=agentic label=sterile arch=additions metric=56 hyp=add_inter beam (0 neighbors incl add_inter/drop; W graph dead at Sun)
- 2026-09-22 20:03 cycle=agentic label=sterile arch=rank metric=23 hyp=Q-redundancy probe Sun+Stapleton (0/23 removable); cross-graft Brent=0; zero+flip brent_hits=0
- 2026-09-22 20:16 cycle=agentic label=sterile arch=additions metric=56 hyp=product-perm CSE (10k perms all total=66 le56=0; greedy rebuild ≠ Sun56 sides)
- 2026-09-22 20:20 cycle=agentic label=sterile arch=additions metric=56 hyp=Laderman sides hill 120k (65→65 imp=0; UV graph connected but local min)
- 2026-09-22 20:23 cycle=agentic label=sterile arch=additions metric=56 hyp=Laderman sides SA 90k (flat plateau; uphill=0); UV mutate probe best=65
- 2026-09-22 20:32 cycle=agentic label=sterile arch=additions metric=56 hyp=Stapleton sides hill (64→63 imp=1 then flat; global baseline still 56)
- 2026-09-22 20:36 cycle=agentic label=sterile arch=support metric=152 hyp=exhaustive k-zero on fixed coords (k=4/5 brent_ok=0); Stapleton sides@63 strict local min
- 2026-09-22 21:19 cycle=agentic label=sterile arch=additions metric=56 hyp=dual U+V side mutate (Stap 3413 neutral; Sun 0 dual-feasible); product signflip breaks Brent
- 2026-09-22 21:26 cycle=agentic label=sterile arch=additions metric=56 hyp=Sun CSE start hill (66→62 plateau; SA@62 flat; same gold as Sun56)
- 2026-09-22 21:40 cycle=agentic label=sterile arch=additions metric=56 hyp=BFS/SA @62→SIDES0@56 same gold (two flat minima; deltas only 0 from 62)
- 2026-09-22 21:42 cycle=agentic label=sterile arch=support metric=152 hyp=1-cell ternary reassign (304 tries brent_ok=0); rank pair-drop 253 pairs no rank-21
- 2026-09-22 21:44 cycle=agentic label=sterile arch=additions metric=56 hyp=2-product UV graft (253 pairs brent=0); CSE@62 add_inter n=0 beam visited=4; support 2-cell 120k brent_hits=24 still 152
- 2026-09-22 21:47 cycle=agentic label=sterile arch=additions metric=56 hyp=whole UV hybrid 9 schemes (cross solve/brent fail; best CSE=66); 3-cell chain+triple rank-drop side sterile

- 2026-09-22 20:00 cycle=36 label=sterile arch=support metric=152 hyp=Stapleton support 152 is not a single-zero local minimum: clearing two nonzero entries simultaneously (on full discrete 

- 2026-09-22 20:01 cycle=37 label=sterile arch=additions metric=56 hyp=Sun W=30 is not tight only under extract/shorten: add_inter and drop_inter moves enable a short beam path to W≤29 (total

- 2026-09-22 20:03 cycle=38 label=sterile arch=rank metric=23 hyp=Sun56 or Stapleton60 has a rank-1 term that is a Q-linear combination of the other 22 (729-d flattening); dropping it yi

- 2026-09-22 20:16 cycle=39 label=sterile arch=additions metric=56 hyp=Reordering the 23 rank-1 products (same Sun56 tensor) changes greedy multi-seed CSE on U,V,W and may yield certified SLP

- 2026-09-22 20:20 cycle=40 label=sterile arch=additions metric=56 hyp=Laderman scheme greedy-CSE sides (total=65, UV mutate graph connected) can gold-preserving hill-climb on U/V/W schedules

- 2026-09-22 20:24 cycle=41 label=sterile arch=additions metric=56 hyp=Laderman sides at total=65 sit in a flat plateau of equal-cost mutate neighbors; simulated annealing (uphill accepts) ca

- 2026-09-22 20:32 cycle=42 label=sterile arch=additions metric=56 hyp=Stapleton greedy-CSE sides (total=64, support=152) have strict downhill gold-preserving mutate edges (unlike flat Laderm

- 2026-09-22 20:36 cycle=43 label=sterile arch=support metric=152 hyp=Stapleton support 152: some 4- or 5-entry simultaneous zero on a small fixed coordinate block satisfies Brent and enable

- 2026-09-22 21:19 cycle=45 label=sterile arch=additions metric=56 hyp=Applying coordinated U+V gold-preserving mutates in one step (not alternating single-side hill) can reach certified tota

- 2026-09-22 21:26 cycle=46 label=sterile arch=additions metric=56 hyp=On Sun's fixed (U,V,W) matrices, greedy CSE schedules (~66) share the same expanded gold as SIDES0@56 but sit in a diffe

- 2026-09-22 21:41 cycle=47 label=sterile arch=additions metric=56 hyp=Sun certificate @62 and literature SIDES0@56 share identical expanded gold; bounded BFS or hot SA from @62 connects to t

- 2026-09-22 21:42 cycle=48 label=sterile arch=support metric=152 hyp=Stapleton support 152: changing one nonzero cell to any other ternary value (−1/0/1) can preserve Brent and enable suppo

- 2026-09-22 21:44 cycle=49 label=sterile arch=additions metric=56 hyp=Sun56 + two Stapleton UV product grafts + re-solved W stays Brent rank-23 and multi-seed CSE can certify total <56 (beyo

- 2026-09-22 21:47 cycle=50 label=sterile arch=additions metric=56 hyp=Cross-scheme whole-matrix pairs (Sun/Stapleton/Perminov U×V) + solved W yield Brent rank-23 factorizations with multi-se

- 2026-09-22 22:04 crash-brief to=1|active=0|detach=0|mid=0|mode=wrap: Timeout post-mortem; Do NOT relaunch the same open-ended search that timed out. Nearby prior hyp (context only)

- 2026-09-22 22:04 crash-brief to=1|active=0|detach=0|mid=1|mode=wrap: Timeout post-mortem; Do NOT relaunch the same open-ended search that timed out. Nearby prior hyp (context only); Lifecycle post-mortem

- 2026-09-22 22:06 crash-brief to=0|active=0|detach=1|mid=1|mode=wrap: Timeout post-mortem; Do NOT relaunch the same open-ended search that timed out. Nearby prior hyp (context only); Lifecycle post-mortem
