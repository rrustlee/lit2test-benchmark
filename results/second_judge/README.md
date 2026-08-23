# Second-Judge Revalidation (W2: single-judge concern)

**New experiment.** Run date: 2026-07-28 (Asia/Shanghai). Status: complete,
**pending allowlist inclusion** (not yet registered in
`analysis/CURRENT_EXPERIMENT_VERSION.md` / `current_experiment_version.json`).
Diagnostic only — no release, no leaderboard.

## Purpose

Reviewer weakness W2: the corrected main analysis relies on a single canonical
judge (Gemini-3.1-Pro-Preview). This experiment re-judges the full
canonical pairwise set with an independent second judge and measures agreement
with the corrected Gemini verdicts.

## Second judge

- Model: `Doubao-Seed-2.0-pro`,
  ByteDance Seed family.
- Why: hard constraint excluded the four participants (GPT 5.2,
  Claude-Sonnet-4.6, GLM-5, DeepSeek-V3.2) and the canonical judge family
  (Gemini). Endpoint probe on 2026-07-28: `Qwen3-Max`, `Kimi-K2`,
  `Mistral-Large` were not accessible through the evaluation endpoint;
  `Doubao-Seed-2.0-pro` is the only accessible model from a family disjoint
  from every participant and from Gemini. No same-family caveat is needed
  (unlike a GLM-family fallback).
- Transport: OpenAI-compatible `POST /chat/completions` on
  `${API_BASE_URL}`, `temperature=1.0`, `max_tokens=1200`
  (pipeline-A chat-judge defaults), timeout 180 s, ≤4 attempts with backoff.
  API key from `API_KEY` env only; never stored or printed.

## Prompt and task presentation (identical to canonical Gemini runs)

- Prompt: verbatim copy of `scripts/run_lit2test_v02_pairwise.py::build_prompt`
  (the native holistic blind pairwise prompt; same text used by
  `run_lit2test_v02_native_gemini_pairwise_judge.py`).
- Tasks: the 2,400 canonical ordered presentations — 1,200 pairs × 2 orders
  from the 10 `pairwise_blind` + 10 `pairwise_blind_reverse`
  `pairwise_tasks.jsonl` files (5 three-model batches + 5 `sonnet_pairs`
  batches), with the 65 mis-oriented expansion40 reverse tasks replaced by the
  frozen `pairwise_blind_reverse_correction65/pairwise_tasks.jsonl` versions.
  Post-replacement orientation audit: 1200/1200 `correctly_swapped`
  (`task_manifest_report.json`).
- Canonical reference for agreement: `corrected_folded_pairs.jsonl`
  (corrected Gemini ordered winners, stability labels, folded winners;
  950 stable / 250 unstable).
- 90-pair subset: the 90 real pairs of the dimension-decomposed audit
  (`audit_tasks_source.jsonl` = byte-identical carry of the original
  dimension-audit task file; md5 `04bc6cd7aecb7ea4a266697ce88559ba`).

## Concurrency probe (subset90, 180 calls)

| workers | calls | ok | fail | throughput/min | p50 lat | p90 lat |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 32 | 32 | 0 | 25.4 | 8.8 s | 10.7 s |
| 8 | 40 | 40 | 0 | 47.5 | 9.2 s | 10.1 s |
| 16 | 52 | 52 | 0 | 83.1 | 8.8 s | 10.6 s |
| 32 | 56 | 56 | 0 | 121.0 | 9.2 s | 10.6 s |

Zero errors at every tier; est. full 2,400 ≈ 20 min at 32 workers → full run
executed at a conservative 16 workers. Full sweep: 2400/2400 valid ordered
judgments, 0 invalid rows, 0 retries exhausted.

## Results (see `analysis.json`)

Subset90 (dimension-audit pairs; deliberately hard: over-samples order-unstable
and adjacent matchups):
- ordered agreement vs Gemini: 141/180 = **0.783**
- ordered agreement on Gemini order-stable subset: 106/120 = **0.883**
- case-level folded agreement: 49/90 = 0.544; on Gemini-stable subset 49/60 = **0.817**
- second-judge stable rate: 70/90 = 0.778

Full 1,200 pairs (2,400 ordered judgments):
- ordered agreement vs Gemini: 1914/2400 = **0.798**
- ordered agreement on Gemini order-stable subset: 1635/1900 = **0.861**
- case-level folded agreement: 759/1200 = **0.633**; on Gemini-stable subset
  759/950 = **0.799**; when both judges decisive 759/980 = **0.774**
- second-judge stability: 992 stable / 208 unstable (0.827; Gemini corrected:
  950/250 = 0.792)
- BT ranking (ordered edges): **GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 >
  DeepSeek-V3.2** — identical to the corrected Gemini BT ranking; the folded
  (flip→tie, tie=0.5) BT ranking is also identical.
- Condorcet: transitive, winner GPT 5.2, beat_counts 3/2/1/0 — same total
  order.
- A-side dist: A 1270 / B 1046 / tie 84 (mild A-preference, comparable to the
  canonical judges).

**Takeaway:** an independent, different-family second judge reproduces the
corrected main ranking exactly (BT + Condorcet, ordered and folded), with
~0.80 ordered agreement overall and ~0.86 on the order-stable subset;
disagreement concentrates where Gemini itself is order-unstable. This
addresses W2 as convergent-validity evidence; it is not a gold label and does
not change the human-calibration status.

## Files (included in this package)

- `judgments.jsonl` — 2,400 parsed ordered judgments (includes the 180 subset
  rows; subset ⊂ full by construction)
- `analysis.json` — full metric set
