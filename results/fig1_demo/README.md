# Figure 1 Paradigm Demo Artifacts

**Figure 1 illustration material only. NOT paper evidence; NOT in CURRENT_EXPERIMENT_VERSION allowlist.**

Real API run artifacts for Figure 1 panels (a) and (b), contrasting evaluation paradigms
on one real Lit2Test context. Panel (c) (six-field contract + blind pairwise) uses existing
mainline data and is not reproduced here.

## Setup

- Context: `smallari_fifth40_034_long_long_context_context_language_llms__v02_fifth40`
  from `data/lit2test_v02_fifth40_smallari_contexts.jsonl` (4 long-context/RAG papers:
  Can Long-Context LLMs Understand Long Contexts? / ALR^2 / ChatQA 2 / Long-Distance Referrals).
- Endpoint: pipeline-standard OpenAI-compatible endpoint (${API_HOST}), run locally.
- Generators: `GPT 5.2`, `GLM-5` (same model IDs as mainline). Judge: `GPT 5.2` (mainline judge).
- Total API calls: 6 (2 generation + 2 free-form judge orders + 2 FPAA scores).
- Run date: 2026-07-27. Runner: `run_fig1_paradigm_demo.py` (this directory).

## Panel (a): schema-free generation + free-form judge

- `stage1_freeform_generations.jsonl` - literature context (same papers/abstracts/limitations
  as mainline input) + unconstrained prompt "Based on these papers, propose a promising
  research idea. Write it however you like." No six-field schema, no structure requirements.
- `stage2a_freeform_judge.jsonl` - no-rubric judge prompt "Which is better and why?",
  run in both A/B orders. Result: judge picked the GPT 5.2 idea in BOTH orders (no flip
  on this pair), with long free-form rationales and no falsifiability requirement.

## Panel (b): future-paper-as-answer (FPAA) scoring

- `stage2b_fpaa_scores.jsonl` - judge scores 0-1 "how well this idea anticipates the
  following published paper". No explicit seed/target paper exists in this neighborhood
  (tfidf-similarity construction), so the answer-key paper was chosen per idea by max
  token overlap - itself an illustration of answer-key arbitrariness:
  - GPT 5.2 idea vs "Scaling Long Context Training Data by Long-Distance Referrals": 0.38
  - GLM-5 idea vs "ALR^2": 0.62
  Note the FPAA ordering (GLM-5 > GPT 5.2) contradicts the free-form judge preference
  (GPT 5.2 in both orders), because each idea is graded against a different answer key.

## Caveats

- Single context, single judge, one pair; anecdotal by construction.
- Prompts and full raw outputs are embedded in each JSONL row (`prompt`, `idea_text`,
  `verdict_text`, `raw_response`).
- Do not aggregate into any leaderboard or main-result table.

## Panel (b) v2: external-anchor FPAA (supersedes v1 scores for the figure)

v1 flaw (user-identified 2026-07-28): v1 answer keys were drawn from the 4
neighborhood papers, which are the generators' *input* context - the ideas
trivially overlap papers they were conditioned on, and the apparent
preference reversal was an artifact of contaminated key choice. Do not use
the 0.38/0.62 v1 numbers in the figure.

v2 (`run_stage2b_v2_external_anchor.py`, `stage2b_v2_external_anchor_scores.jsonl`,
run 2026-07-28, judge GPT 5.2, single call per cell, temperature 1.0):
both ideas scored against each of FOUR real external papers (verified on
arXiv, absent from the input context). Anchor set was chosen deliberately
to span the neighborhood's two plausible future trajectories - two
RAG-mechanism papers and two long-context training-data papers - and ALL
tried anchors are reported (no undisclosed search):

| anchor | trajectory | GPT 5.2 idea | GLM-5 idea | winner |
|---|---|---|---|---|
| Self-Route (arXiv:2407.16833) | RAG mechanism | 0.27 | 0.22 | GPT |
| OP-RAG (arXiv:2409.01666) | RAG mechanism | 0.42 | 0.22 | GPT |
| In-context Pretraining (arXiv:2310.10638) | training data | 0.28 | 0.62 | GLM |
| Data Engineering 128K (arXiv:2402.10171) | training data | 0.12 | 0.18 | GLM |

Preference reversal is real under clean external anchors: the free-form
judge in (a) picked the GPT idea in both orders, and RAG-trajectory anchors
agree, but training-data-trajectory anchors flip the ranking (ICP: GLM 0.62
vs GPT 0.28). Each idea anticipates a different future trajectory of the
same neighborhood, so the FPAA verdict depends entirely on which trajectory
the chosen "future paper" happens to come from - the single-trajectory
critique made concrete. Recommended figure pair: OP-RAG vs ICP (largest
clean contrast, one anchor per trajectory).
