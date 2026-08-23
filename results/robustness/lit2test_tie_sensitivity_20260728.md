# Lit2Test Tie-Sensitivity Analysis (Order-Sensitive Cases), 2026-07-28

中文简介：回应审稿弱点 W3（"剔除 21% order-sensitive case 再报 strict ordering 有循环放大之嫌"）。本报告不剔除任何 case：把全部 250 个 order-sensitive case 分别按保守口径（记平局）和对抗口径（全部判给每对中的排序劣势方）重新计入，重算六个模型对的 head-to-head、Condorcet 与 folded BT，并在保守口径下做 10,000 次 case-level bootstrap。纯本地重算，不调 API，不改动任何冻结产物。

- Status: `pass`
- Date: `2026-07-28`
- Case-level input: `outputs/lit2test_v02_expansion40_adjudicated40/pairwise_blind_reverse_correction65/corrected_folded_pairs.jsonl` (corrected fold, 1,200 rows)
- Cross-check: per-pair stable-win and sensitive counts match `analysis/lit2test_corrected_gemini_main_results.json` (`corrected.folded`) exactly
- Coverage: `1200` folded cases = 6 model pairs x 200 contexts; `950` order-stable, `250` order-unstable (20.8%)
- Reference ordering under audit: `GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 > DeepSeek-V3.2`
- Bootstrap: `10000` replicates, seed `20260721`, unit = folded case

## Method

1. Load the 1,200 corrected folded cases (each canonical pair folded over its original and reverse Gemini judgments). A case is `order-stable` if both orders agree (the agreed winner is the folded winner) and `order-unstable` otherwise. Verified counts: 950 stable / 250 unstable, 200 cases per model pair.
2. **Scheme A (conservative)**: each of the 250 order-sensitive cases is scored as a tie (0.5 win to each side) and merged with the 950 stable outcomes. Head-to-head majorities, Condorcet relation, and folded BT (MM fit, ties as half-wins, centered log abilities) are recomputed.
3. **Scheme B (adversarial)**: every order-sensitive case is awarded as a full win to the lower-ranked model of its pair under the reference ordering (worst case for the reported ordering). Same statistics recomputed.
4. **Bootstrap (Scheme A)**: 10,000 case-level bootstrap replicates resampling the 1,200 folded cases with replacement (sensitive cases carried as 0.5/0.5 ties), refitting the folded BT each time, and counting how often the full reference ordering is recovered.

## Folded case-level data (corrected)

| Model pair | Stable wins (higher) | Stable wins (lower) | Order-sensitive | Cases |
|---|---:|---:|---:|---:|
| `GPT 5.2 \| Claude-Sonnet-4.6` | GPT 5.2 90 | Claude-Sonnet-4.6 38 | 72 | 200 |
| `GPT 5.2 \| GLM-5` | GPT 5.2 154 | GLM-5 7 | 39 | 200 |
| `GPT 5.2 \| DeepSeek-V3.2` | GPT 5.2 180 | DeepSeek-V3.2 4 | 16 | 200 |
| `GLM-5 \| Claude-Sonnet-4.6` | Claude-Sonnet-4.6 143 | GLM-5 18 | 39 | 200 |
| `GLM-5 \| DeepSeek-V3.2` | GLM-5 93 | DeepSeek-V3.2 46 | 61 | 200 |
| `DeepSeek-V3.2 \| Claude-Sonnet-4.6` | Claude-Sonnet-4.6 166 | DeepSeek-V3.2 11 | 23 | 200 |

Total stable 950, total sensitive 250. "Higher"/"lower" refer to the reference ordering.

## Scheme A: sensitive cases as ties (conservative)

| Model pair | Score (higher) | Score (lower) | Majority | Margin |
|---|---:|---:|---|---:|
| `GPT 5.2 \| Claude-Sonnet-4.6` | 126.0 | 74.0 | GPT 5.2 | +52.0 |
| `GPT 5.2 \| GLM-5` | 173.5 | 26.5 | GPT 5.2 | +147.0 |
| `GPT 5.2 \| DeepSeek-V3.2` | 188.0 | 12.0 | GPT 5.2 | +176.0 |
| `GLM-5 \| Claude-Sonnet-4.6` | 162.5 | 37.5 | Claude-Sonnet-4.6 | +125.0 |
| `GLM-5 \| DeepSeek-V3.2` | 123.5 | 76.5 | GLM-5 | +47.0 |
| `DeepSeek-V3.2 \| Claude-Sonnet-4.6` | 177.5 | 22.5 | Claude-Sonnet-4.6 | +155.0 |

- Condorcet: beat counts `{GPT 5.2: 3, Claude-Sonnet-4.6: 2, GLM-5: 1, DeepSeek-V3.2: 0}`; winner `GPT 5.2`; transitive, no cycle.
- Folded BT centered log abilities: GPT 5.2 `1.2709`, Claude-Sonnet-4.6 `0.7458`, GLM-5 `-0.7347`, DeepSeek-V3.2 `-1.2821`.
- BT ranking: `GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 > DeepSeek-V3.2`.
- **Conclusion: the reference ordering is preserved strictly** (all six head-to-head majorities strict, Condorcet relation transitive and identical, BT ranking identical).

## Scheme B: every sensitive case awarded against the ordering (adversarial)

| Model pair | Score (higher) | Score (lower = stable + all sensitive) | Adversarial margin | Flips? |
|---|---:|---:|---:|---|
| `GPT 5.2 \| Claude-Sonnet-4.6` | 90 | 110 | **-20** | **yes** |
| `GLM-5 \| DeepSeek-V3.2` | 93 | 107 | **-14** | **yes** |
| `GLM-5 \| Claude-Sonnet-4.6` | 143 | 57 | +86 | no |
| `GPT 5.2 \| GLM-5` | 154 | 46 | +108 | no |
| `DeepSeek-V3.2 \| Claude-Sonnet-4.6` | 166 | 34 | +132 | no |
| `GPT 5.2 \| DeepSeek-V3.2` | 180 | 20 | +160 | no |

- **Two pairwise relations flip**: `GPT 5.2 vs Claude-Sonnet-4.6` (90 vs 110) and `GLM-5 vs DeepSeek-V3.2` (93 vs 107). Relative to the Scheme-A baseline (all sensitive cases as ties), the GPT-Claude majority inverts once >= 53 of its 72 sensitive cases are awarded to Claude-Sonnet-4.6, and the GLM-DeepSeek majority inverts once >= 48 of its 61 sensitive cases are awarded to DeepSeek-V3.2. These are the two most fragile pairs.
- Adversarial Condorcet: beat counts `{Claude-Sonnet-4.6: 3, GPT 5.2: 2, DeepSeek-V3.2: 1, GLM-5: 0}`; winner `Claude-Sonnet-4.6`; ranking `Claude-Sonnet-4.6 > GPT 5.2 > DeepSeek-V3.2 > GLM-5` (transitive, no cycle).
- Adversarial folded BT (margin-weighted over all six pairs): GPT 5.2 `0.7221`, Claude-Sonnet-4.6 `0.6914`, GLM-5 `-0.5991`, DeepSeek-V3.2 `-0.8144`; BT ranking stays `GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 > DeepSeek-V3.2`, but the GPT-vs-Claude BT gap shrinks from `0.525` (Scheme A) to `0.031`.
- **Conclusion: the ordering does NOT fully survive the adversarial assignment.** The four non-adjacent-in-strength relations survive with margins >= 86/200; the two closest relations (GPT 5.2 vs Claude-Sonnet-4.6 and GLM-5 vs DeepSeek-V3.2) invert under the worst case, so those adjacent-pair orderings depend on how the sensitive cases are resolved. The adversarial scenario awards all 250 sensitive cases against the ordering simultaneously, which is far more extreme than any plausible judge behavior, but it bounds the claim honestly.

## Bootstrap (Scheme A, 10,000 replicates)

- Full reference ordering `GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 > DeepSeek-V3.2` recovered in `10000/10000` replicates (recovery rate `1.0000`).
- Rank distribution: `{GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 > DeepSeek-V3.2: 10000}`.

## One-line conclusions

- Scheme A (ties): ordering preserved strictly, all six majorities strict, Condorcet transitive, bootstrap recovery 100%.
- Scheme B (adversarial): four of six pairwise relations survive (minimum margin 86/200); the two adjacent pairs `GPT 5.2 | Claude-Sonnet-4.6` (margin -20) and `GLM-5 | DeepSeek-V3.2` (margin -14) flip, and the adversarial Condorcet winner becomes Claude-Sonnet-4.6.

## Draft sentence for the paper (English)

> The reported ordering is unchanged when all 250 order-sensitive cases are scored as ties rather than excluded: every head-to-head majority, the Condorcet relation, and the folded Bradley-Terry ranking preserve GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 > DeepSeek-V3.2, and the full ordering is recovered in 10,000 of 10,000 case-level bootstrap replicates. Under the far stronger adversarial assumption that every sensitive case is awarded against the ordering, the four largest pairwise relations still survive (minimum margin 143 vs 57 of 200), but the two closest pairs, GPT 5.2 vs Claude-Sonnet-4.6 (90 vs 110) and GLM-5 vs DeepSeek-V3.2 (93 vs 107), would invert; the adjacent-pair orderings therefore hold under the tie treatment but are not robust to a worst-case resolution of the order-sensitive cases.

## Boundary

- This is a diagnostic sensitivity analysis of the corrected Gemini main experiment; it is not a leaderboard and the LLM judge is not a gold label.
- Machine-readable companion: `analysis/lit2test_tie_sensitivity_20260728.json`.
