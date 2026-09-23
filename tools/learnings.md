# Research learnings (agentic director)

Hard facts (do not re-run these neighborhoods with the same seeds/moves):

- Sun W nullspace dim=0 given U,V — cannot vary W alone for additions.
- Signflip + greedy W CSE always lands >=57 (improvements=0 overnight).
- UV-affine mutate+solve W: no mass at cost<=56 (scored tens of thousands).
- Stapleton 2/3-edit: accept_rate~8.5% but improved=0 over ~2M edits (plateau at 152).
- Scheme CSE Stapleton/Perminov/Laderman bottoms ~64–66 with le56=0.
- Multi-seed support stuck at 152; flipgraph/rank-drop found no exact rank<23.

Targets (any win counts): certified SLP additions <56 @ rank 23; support <152; rank <23.
Metric choice: OPPORTUNISTIC — director picks additions/support/rank each cycle from
ledger + hypotheses; cross-pollination encouraged. No fixed priority order (human
“additions first” was only a guess about what might move sooner).

Baselines: Sun56 adds=56, Stapleton support=152, rank=23.

## Updates

(appended by agentic_director after each cycle)

- 2026-09-23 14:57 policy: opportunistic metric choice (additions/support/rank); cross-pollination OK; no fixed priority order

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

- 2026-09-23 10:15 TIMEOUT cycle=63 mode=wrap heartbeat=running Sun signflip max-k=2 eta_s=240; recent_tools=tools/slp_subset_signflip_rebuild.py,tools/agentic_director.py,tools/director_dashboard.py → next: smoke-bound + early agent_cycle_result.json

- 2026-09-23 10:15 crash-brief to=1|active=0|detach=1|mid=1|mode=extend: Timeout post-mortem; Do NOT relaunch the same open-ended search that timed out. Nearby prior hyp (context only); Lifecycle post-mortem

- 2026-09-23 12:00 TIMEOUT cycle=64 mode=extend heartbeat=support_three_cell_rotate 40k eta_s=60; recent_tools=tools/support_three_cell_rotate.py,tools/support_cell_swap.py,tools/slp_subset_signflip_rebuild.py → next: smoke-bound + early agent_cycle_result.json

- 2026-09-23 12:00 crash-brief to=2|active=0|detach=1|mid=1|mode=extend: Timeout post-mortem; Do NOT relaunch the same open-ended search that timed out. Nearby prior hyp (context only); Lifecycle post-mortem

- 2026-09-23 13:32 TIMEOUT cycle=65 mode=extend heartbeat=slp_sun62_uphill_shell smoke eta_s=180; recent_tools=tools/slp_sun62_uphill_shell.py,tools/support_three_cell_rotate.py,tools/support_cell_swap.py → next: smoke-bound + early agent_cycle_result.json

- 2026-09-23 13:32 crash-brief to=3|active=0|detach=1|mid=1|mode=extend: Timeout post-mortem; Do NOT relaunch the same open-ended search that timed out. Nearby prior hyp (context only); Lifecycle post-mortem

- 2026-09-23 14:54 cycle=66 label=sterile arch=rank metric=23 hyp=On Sun56 or Stapleton rank-23, flipping signs on only one factor (U-only, V-only, or W-only) of a single product preserv

- 2026-09-23 14:55 cycle=67 label=sterile arch=additions metric=56 hyp=Sun literature SIDES0@56 and CSE-hill certificate @62 share expanded gold but differ in U,V,W factor matrices; if matric

- 2026-09-23 14:55 cycle=68 label=sterile arch=support metric=152 hyp=Stapleton support 152: a non-identity discrete orbit seed (transpose, S3 relabel, factor cycle) yields support<152 after

- 2026-09-23 14:56 cycle=69 label=sterile arch=additions metric=56 hyp=Sun SIDES0@56 (or CSE certificate @62) has a W/U/V intermediate removable via drop_inter while preserving expanded gold,

- 2026-09-23 14:56 cycle=70 label=sterile arch=additions metric=56 hyp=Sun SIDES0@56 (or CSE @62) admits a gold-preserving common_pair extract on U/V/W (shared ±pair in ≥2 finals) that lowers

- 2026-09-23 14:56 cycle=71 label=sterile arch=additions metric=56 hyp=Sun SIDES0@56 or CSE @62 has a multi-term final rewritable with fewer refs using existing basis vectors (exhaustive 1-/2

- 2026-09-23 15:00 cycle=72 label=sterile arch=additions metric=56 hyp=Exhaustive add_inter (≥2 final shorten) on Sun @56/@62 or Stapleton CSE @64 yields a gold-preserving net certified drop;

- 2026-09-23 15:11 cycle=73 label=sterile arch=support metric=152 hyp=Stapleton Brent-ok two-cell reassignments can show support<152 before greedy zeroing, or lift below 152 when raw support

- 2026-09-23 15:12 cycle=74 label=sterile arch=additions metric=56 hyp=Stapleton sides certificate @63 admits a second gold-preserving add_inter (depth-2 chain) lowering certified total below

- 2026-09-23 15:12 cycle=75 label=sterile arch=additions metric=56 hyp=Relaxing add_inter to ≥1 final shorten (not ≥2) exposes gold-preserving moves on Sun @62/@56 that lower certified total 

- 2026-09-23 15:14 cycle=76 label=sterile arch=additions metric=56 hyp=Sun @62: cost-neutral relaxed add_inter neighbors (56 distinct schedules) sit in alternate mutate components; 2k-round d

- 2026-09-23 15:14 cycle=77 label=sterile arch=additions metric=56 hyp=Sun SIDES0@56 and CSE certificate @62 are one mutate/relaxed-add_inter step apart on identical gold (explaining unreacha

- 2026-09-23 15:20 cycle=78 label=sterile arch=additions metric=56 hyp=Sun @56 and CSE @62 connect within depth-2 on gold graph (relaxed add_inter then mutate), enabling descent from 62 towar

- 2026-09-23 15:21 cycle=79 label=sterile arch=support metric=152 hyp=Fresh-seed Stapleton random 2/3-edit smoke (8k, p3=0.4) finds Brent-ok edits that greedy-zero to support<152 (2M overnig

- 2026-09-23 15:21 cycle=80 label=sterile arch=rank metric=23 hyp=Sun/Stapleton product matrices have rank<23 over GF(2) or GF(3), indicating mod-p redundancy usable for exact rank-22; s

- 2026-09-23 cycle=81 label=sterile arch=additions metric=56 hyp=Sun56 two-of-three term sign flips + CSE (5k best=60 le56=0); side shuffle-zero support still 152

- 2026-09-23 15:23 cycle=81 label=sterile arch=additions metric=56 hyp=Sun56 Brent-ok per-term two-of-three (U,V,W) sign flips explore a scheduling-equivalent UVW family that greedy multi-see

- 2026-09-23 cycle=82 label=sterile arch=additions metric=56 hyp=CSE seed fan on Sun56 rows (384 seeds best=66 not 56); flipgraph warm Stapleton 2.5k still support 152

- 2026-09-23 cycle=83 label=sterile arch=additions metric=56 hyp=relaxed add_inter portals @56/@62 + 220 strict mutate each (30+40 portals, still 56/62)

- 2026-09-23 cycle=84 label=sterile arch=additions metric=56 hyp=relaxed beam 800 states @62 all cost 62; random rank23 support brent=0; Stapleton 1-flip brent=0

- 2026-09-23 cycle=85 label=sterile arch=additions metric=56 hyp=interleave relaxed+mutate walks @62 (40×80 best=62); W SA 3.2k seed=850002 acc=0

- 2026-09-23 cycle=86 label=sterile arch=rank metric=23 hyp=single-term drop rank-22 Brent (sun+stap 0/46); support 3-edit 1500 seed=860003 still 152

- 2026-09-23 cycle=87 label=sterile arch=additions metric=56 hyp=W addinter beam @56/@62 neighbors=0; U/V-only hill flat; pair-zero sample brent=0

- 2026-09-23 cycle=88 label=sterile arch=additions metric=56 hyp=tensor orbit CSE score best=66; term-merge rank 253 pairs brent=0

- 2026-09-23 cycle=89 label=sterile arch=support metric=152 hyp=support SA 2k 2-edit (acc=2 still 152); joint UV side mutate @56 imp=0

- 2026-09-23 cycle=90 label=sterile arch=support metric=152 hyp=coord triple-zero 207 cells brent=0; GF5/7 rank 23; Stap hill 1800 @64 flat

- 2026-09-23 cycle=91 label=sterile arch=additions metric=56 hyp=sides hill @62 1800 flat 62; triple side mutate @56 hits=0; rank+flip still 23

- 2026-09-23 cycle=92 label=sterile arch=additions metric=56 hyp=sides SA @62 2800 flat; Laderman beam 700@65 flat; support raw-improve hill brent=0

- 2026-09-23 cycle=93 label=sterile arch=additions metric=56 hyp=uphill shell @62 (900 trials shells@63=0); stap UV 1-edit+solve W brent=55 support still 152

- 2026-09-23 cycle=94 label=sterile arch=additions metric=56 hyp=relaxed uphill @62 exhaustive (56 hits all cost 62, no +1 shells); same-term UV support brent=2 still 152

- 2026-09-23 cycle=95 label=sterile arch=additions metric=56 hyp=Sun/Stap UV mosaic+solve W (900 brent=0); relax hist @56 only 56; 1-term UV swap brent=0

- 2026-09-23 cycle=96 label=sterile arch=support metric=152 hyp=double-zero sample brent=0; mutate sample flat @56/@62; flipgraph 4k rank23_seen=0

- 2026-09-23 cycle=97 label=sterile arch=rank metric=23 hyp=Stap flip-walk rank drop (1154 brent ok, rank stays 23); sun/stap same 729-d tensor; Stap@63 hill flat

- 2026-09-23 15:24 cycle=82 label=sterile arch=additions metric=56 hyp=Sun56 certified total 56 is underestimated by default multi-seed CSE; fanning hundreds of independent greedy-CSE seeds o

- 2026-09-23 15:24 cycle=83 label=sterile arch=additions metric=56 hyp=Relaxed add_inter portals at Sun SIDES0@56 (and @62) reach alternate gold-preserving side certificates; one strict mutat

- 2026-09-23 15:27 cycle=84 label=sterile arch=additions metric=56 hyp=Depth-3 relaxed add_inter beam (≤800 states) from Sun CSE @62 reaches alternate side certificates with certified total <

- 2026-09-23 15:40 cycle=85 label=sterile arch=additions metric=56 hyp=Random interleaved relaxed add_inter + strict downhill mutate walks from Sun @62 (many short trajectories) escape the fl

- 2026-09-23 15:41 cycle=86 label=sterile arch=rank metric=23 hyp=Sun56 or Stapleton60 has a redundant rank-1 term: deleting one product row triple yields an exact Brent-ok rank-22 facto

- 2026-09-23 15:42 cycle=87 label=sterile arch=additions metric=56 hyp=Sun SIDES0 W=30 is not add_inter/extract-tight: bounded W-only addinter beam finds gold-preserving path to W≤29 (certifi

- 2026-09-23 15:42 cycle=88 label=sterile arch=additions metric=56 hyp=A discrete matmul-tensor symmetry (S3 relabel / transpose / factor cycle) of Sun56 UVW yields Brent-ok equivalent factor

- 2026-09-23 15:42 cycle=89 label=sterile arch=support metric=152 hyp=Stapleton support=152 is a SA-trappable local basin: 2-edit simulated annealing (uphill accepts) finds Brent-ok states t

- 2026-09-23 15:43 cycle=90 label=sterile arch=support metric=152 hyp=Stapleton support=152 can drop when the same (term, index) is zeroed simultaneously in U, V, and W (coordinated triple-z

- 2026-09-23 15:43 cycle=91 label=sterile arch=additions metric=56 hyp=Sun CSE certificate @62 (total=62) is not a sides-mutate local minimum: 1800-round gold-preserving sides hill descends t

- 2026-09-23 15:44 cycle=92 label=sterile arch=additions metric=56 hyp=Simulated annealing on full Sun sides @62 (uphill accepts) escapes the cost-62 plateau and reaches certified total 56 on

- 2026-09-23 15:45 cycle=93 label=sterile arch=additions metric=56 hyp=Sun @62 admits cost+1 (63) gold-preserving side shells via one strict mutate; downhill hill from each shell reaches cert

- 2026-09-23 15:45 cycle=94 label=sterile arch=additions metric=56 hyp=Sun @62 admits cost+1 shells via relaxed add_inter (not strict mutate); downhill hill from those shells reaches total <6

- 2026-09-23 15:46 cycle=95 label=sterile arch=additions metric=56 hyp=Random per-term Sun/Stapleton UV mosaics (re-solved W) produce Brent-ok rank-23 factorizations in a new basin with certi

- 2026-09-23 15:47 cycle=96 label=sterile arch=support metric=152 hyp=Stapleton support=152 yields Brent-ok states under simultaneous two-entry zeroing (sparse double-zero), which greedy-zer

- 2026-09-23 15:47 cycle=97 label=sterile arch=rank metric=23 hyp=Stapleton rank-23 admits Brent-preserving single-coefficient flips whose compact rank drops below 23 (local rank-reducti

- 2026-09-23 cycle=98 label=sterile arch=additions metric=56 hyp=relaxed add_inter then strict mutate depth-2 chain from SIDES0 (900 chains best=56); side rank two-flip Stap brent=295 best_rank=23; side orbit exhaustive_zero min support=152

- 2026-09-23 cycle=99 label=sterile arch=additions metric=56 hyp=Stapleton @63 alternate gold basin relaxed→strict chains to total≤56 (900 chains best=63); side flip+plus from Stap rank23_seen=31 support=152

- 2026-09-23 cycle=100 label=sterile arch=additions metric=56 hyp=Stapleton UV greedy CSE seed fan reaches total<56 (256 seeds best=71); side rank three-flip Stap brent=92 best_rank=23

- 2026-09-23 cycle=101 label=sterile arch=support metric=152 hyp=pairwise value-swap on nonzero Stap cells + exhaustive_zero (2000 pairs brent=2 best=152); side Stap orbit CSE all 71

- 2026-09-23 cycle=102 label=sterile arch=support metric=152 hyp=flip walk from Perminov58 reaches rank-23 support<152 (3500 steps best=175); side Stap@63 relaxed add_inter all cost 63

- 2026-09-23 cycle=103 label=sterile arch=support metric=152 hyp=flip walk Sun56 to support<152 (3500 best=175); side strict depth-2 mutate @56 best=56

- 2026-09-23 cycle=104 label=sterile arch=additions metric=56 hyp=relaxed add_inter BFS from SIDES0@56 (700 states best=56); side 3-cell rotate 1800 brent=1 support=152

- 2026-09-23 cycle=105 label=sterile arch=rank metric=23 hyp=schoolbook 8% plus walk reaches rank<23 (4500 steps brent0=15 best_rank=27); side flip+exhaustive_zero Stap brent=810 support=152

- 2026-09-23 cycle=106 label=sterile arch=additions metric=56 hyp=interleave relax+mutate from SIDES0@56 (50×90 best=56); side rank flip Sun brent0=841 best_rank=23

- 2026-09-23 cycle=107 label=sterile arch=support metric=152 hyp=Sun56 flip+plus to support<152 (3200 rank23=129 best=175); side strict depth-3 mutate @56 best=56

- 2026-09-23 cycle=108 label=sterile arch=support metric=152 hyp=random sparse rank-23 UV+solve W yields Brent support<152 (1800 trials brent=0); side Stap plus-flip rank best=23

- 2026-09-23 cycle=109 label=sterile arch=additions metric=56 hyp=dense random rank-23 UV (4–8 nnz) Brent+CSE<56 (850 brent=0); side schoolbook rank23 hunt 5500 rank23_seen=0

- 2026-09-23 cycle=110 label=sterile arch=additions metric=56 hyp=23 single-term Sun←Stap UV grafts+solve W yield Brent+CSE<56 (brent=0); side Stap@63 drop_inter hits=0

- 2026-09-23 cycle=111 label=sterile arch=additions metric=56 hyp=23 full triple (U,V,W) term graft Sun←Stap (brent=0); side four-flip Stap brent=24 best_rank=23

- 2026-09-23 cycle=112 label=sterile arch=additions metric=56 hyp=k=2 triple grafts Sun←Stap (600 brent=0); side GF2/3 rank=23 all; Perminov score_uvw None

- 2026-09-23 cycle=113 label=sterile arch=additions metric=56 hyp=22+1 Sun/Stap hybrid (23 exhaustive brent=0); side k=3 graft 350 brent=0

- 2026-09-23 15:48 cycle=98 label=sterile arch=additions metric=56 hyp=One relaxed add_inter portal at Sun SIDES0@56 followed by one strict gold-preserving mutate reaches a side certificate w

- 2026-09-23 15:49 cycle=99 label=sterile arch=additions metric=56 hyp=Stapleton sides @63 uses a different expanded-gold basin than Sun SIDES0@56; relaxed add_inter then strict mutate depth-

- 2026-09-23 15:50 cycle=100 label=sterile arch=additions metric=56 hyp=Stapleton rank-23 UV (same 729-d tensor as Sun56) admits greedy row-CSE side certificates with certified total <56 for s

- 2026-09-23 15:50 cycle=101 label=sterile arch=support metric=152 hyp=Stapleton support=152 is not minimal under pairwise value-swap edits (exchange two nonzero cell values, not independent 

- 2026-09-23 15:51 cycle=102 label=sterile arch=support metric=152 hyp=Flip-graph random walks from Perminov58 (support 175, same 729-d tensor) reach Brent rank-23 states with support<152—the

- 2026-09-23 15:51 cycle=103 label=sterile arch=support metric=152 hyp=Flip-graph walks from Sun56 (support 175, same 729-d tensor as Stapleton@152) reach Brent rank-23 compact factorizations

- 2026-09-23 15:54 cycle=104 label=sterile arch=additions metric=56 hyp=Relaxed add_inter BFS (depth≤3, ≤700 states) from Sun SIDES0@56—not from CSE@62—discovers gold-preserving side certifica

- 2026-09-23 15:56 cycle=105 label=sterile arch=rank metric=23 hyp=Schoolbook rank-27 admits Brent-exact rank<23 within 4.5k flip+plus steps at 8% plus rate (prior 4% plus hunt never reac

- 2026-09-23 15:57 cycle=106 label=sterile arch=additions metric=56 hyp=Interleaved relaxed add_inter + strict downhill mutate walks from Sun SIDES0@56 (50×90 steps, not @62) escape the global

- 2026-09-23 15:58 cycle=107 label=sterile arch=support metric=152 hyp=Sun56 flip+plus walk (5% plus, rank-23 compact states) reaches support<152—flip-only from Sun stuck at 175 but plus move

- 2026-09-23 15:58 cycle=108 label=sterile arch=support metric=152 hyp=Uniform random sparse rank-23 (U,V) with ternary-solved W produces Brent-ok 3×3 factorizations outside literature basins

- 2026-09-23 15:59 cycle=109 label=sterile arch=additions metric=56 hyp=Denser random rank-23 UV (4–8 nonzero entries per row, solved W) hits Brent-ok and greedy CSE certified total <56—light 

- 2026-09-23 16:00 cycle=110 label=sterile arch=additions metric=56 hyp=Replacing exactly one Sun56 rank-1 term's (U,V) row with Stapleton's matching row (23 deterministic grafts, re-solved W)

- 2026-09-23 16:00 cycle=111 label=sterile arch=additions metric=56 hyp=Replacing one full Sun56 rank-1 triple (U,V,W)_t with Stapleton's matching term (not UV-only graft) preserves Brent for 

- 2026-09-23 16:00 cycle=112 label=sterile arch=additions metric=56 hyp=Two-term full (U,V,W) grafts from Stapleton into Sun (600 random pairs) yield Brent-ok factorizations with CSE total <56

- 2026-09-23 16:01 cycle=113 label=sterile arch=additions metric=56 hyp=Hybrid factorizations keeping exactly one Sun56 rank-1 triple and grafting Stapleton on the other 22 terms (23 exhaustiv

- 2026-09-23 16:02 cycle=114 label=sterile arch=rank metric=27 hyp=Schoolbook Brent-residual descent (5000 steps) visits Brent=0 often but compact rank stays 27; Sun56 support orbit min=175; Q-redundancy 0/23

- 2026-09-23 16:06 cycle=115 label=sterile arch=support metric=152 hyp=Greedy batch hill-climb on Brent=0 flips from Stap (180×36) — improvements=0; 152 is strict flip-local min; Laderman UV graft 1/23 Brent CSE=66; 22+Laderman hybrid Brent=0

- 2026-09-23 16:09 cycle=116 label=sterile arch=support metric=152 hyp=Two-flip greedy Brent batch from Stap (90×24) — improvements=0; 152 also 2-flip local min; Perm UV graft 1/23 CSE=68; Stap orbit CSE min=71

- 2026-09-23 16:07 cycle=117 label=sterile arch=additions metric=56 hyp=Stap@63 strict add_inter exhaust hits=0; relaxed min@63=63 (82 nbrs); Sun relaxed min=56; 253 term merges Brent=0; signflip CSE min=62

- 2026-09-23 16:08 cycle=118 label=sterile arch=additions metric=56 hyp=Sun/Stap per-side cross combo (8) — only SSS gold-valid; 3-flip support sample min=152; 3-flip rank min=23

- 2026-09-23 16:08 cycle=119 label=sterile arch=rank metric=23 hyp=Drop one term + solve W on Sun/Stap — 0/23 Brent rank-22 each; CSE@62 W add_inter beam 0 neighbors; greedy zero Stap 152

- 2026-09-23 16:09 cycle=120 label=sterile arch=additions metric=56 hyp=k=4 Stap→Sun triple graft 500 samples brent_ok=0; greedy compact-rank flip 0 imp; double-zero Stap 0 Brent hits

- 2026-09-23 16:09 cycle=121 label=sterile arch=additions metric=56 hyp=Depth-2 strict add_inter @ SIDES0@56 — level1_hits=0; Perm+1 Sun Brent=0; Stap CSE fan min=71; Stap plus support 152

- 2026-09-23 16:18 cycle=122 label=sterile arch=additions metric=56 hyp=Laderman k=2→Sun graft 550 brent_ok=0; rebuild_sides_from_uvw smoke aborted (slow); support 1200 edits still 152

- 2026-09-23 16:19 cycle=123 label=sterile arch=additions metric=56 hyp=Random Sun/Stap partition graft k=5..18 (450) brent_ok=0; Laderman flip support 153; @62 interleave best=62

- 2026-09-23 16:20 cycle=124 label=sterile arch=support metric=152 hyp=Stap 1-cell UV perturb+solve W (1700) brent_ok=54 best_support=152; W-hill @62 flat; depth2 chain @62 flat

- 2026-09-23 16:21 cycle=125 label=sterile arch=additions metric=56 hyp=Sun 1-cell UV perturb CSE (1600) brent_ok=80 best_cse=66; 3-flip greedy support 0 imp; relaxed-strict @56 flat

- 2026-09-23 16:22 cycle=126 label=sterile arch=rank metric=27 hyp=Schoolbook 10% plus compact hunt brent0=176 best_compact=27; Stap 2-cell UV perturb 1/1400; interleave @56 best=56

- 2026-09-23 16:01 cycle=114 label=sterile arch=rank metric=27 hyp=Schoolbook rank-27 walks that always accept strict Brent-residual decreases (plus occasional uphill) visit Brent=0 often

- 2026-09-23 16:05 cycle=115 label=sterile arch=support metric=152 hyp=Stapleton support=152 is not a greedy local minimum under Brent=0 flips: batch hill-climb (pick best of 36 flips per ste

- 2026-09-23 16:06 cycle=116 label=sterile arch=support metric=152 hyp=Stapleton support=152 is a single-flip local minimum but not a two-flip local minimum: greedy batch descent using two co

- 2026-09-23 16:06 cycle=117 label=sterile arch=additions metric=56 hyp=Stapleton sides@63 (secondary additions basin vs Sun SIDES0@56) admits strict add_inter neighbors lowering certified tot

- 2026-09-23 16:07 cycle=118 label=sterile arch=additions metric=56 hyp=Mixing Sun SIDES0@56 and Stapleton sides@63 per side (U/V/W independently) yields gold-valid SLP certificates with certi

- 2026-09-23 16:07 cycle=119 label=sterile arch=rank metric=23 hyp=Some rank-1 term in Sun56 or Stapleton60 is redundant after UV restriction: delete one term, solve W on the 22×9 system,

- 2026-09-23 16:08 cycle=120 label=sterile arch=additions metric=56 hyp=Four-term full (U,V,W) grafts from Stapleton into Sun (k=4, 500 samples) achieve Brent-ok on the shared tensor where k=1

- 2026-09-23 16:08 cycle=121 label=sterile arch=additions metric=56 hyp=Sun SIDES0@56 admits strict add_inter with ≥2 final shortenings (level-1); chaining two such moves (depth-2) reaches cer

- 2026-09-23 16:18 cycle=122 label=sterile arch=additions metric=56 hyp=Two-term full triple grafts from Laderman into Sun (550 samples) Brent-close on the shared 729-d tensor where Stap↔Sun g

- 2026-09-23 16:19 cycle=123 label=sterile arch=additions metric=56 hyp=Random Sun/Stap partition grafts with 5–18 donor terms (450 samples) Brent-close on the shared tensor—partial masks may 

- 2026-09-23 16:19 cycle=124 label=sterile arch=support metric=152 hyp=Single-entry UV perturbations on Stapleton (re-solved W, 1700 trials) produce Brent-ok rank-23 factorizations in a neigh

- 2026-09-23 16:20 python cycle=126 label=flat arch=support metric=152 tool=support_same_term_uv_edit.py

- 2026-09-23 16:21 cycle=125 label=sterile arch=additions metric=56 hyp=Single-entry UV perturbations on Sun56 (re-solved W, 1600 trials) hit Brent-ok neighborhoods with greedy CSE certified t

- 2026-09-23 16:21 cycle=126 label=sterile arch=rank metric=27 hyp=Plus-heavy schoolbook walk (10% plus, 4.5k steps) visits Brent=0 often enough that compact_rank drops below 23—rank-27 s

- 2026-09-23 16:23 python cycle=128 label=flat arch=support metric=152 tool=support_random_rank23.py
