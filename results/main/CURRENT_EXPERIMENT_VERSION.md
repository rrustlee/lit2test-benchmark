# Current Experiment Version

Date: 2026-07-23

Current active result version: **corrected Gemini judge + 4 participant models** (orientation-corrected main experiment, completed human calibration, completed manipulation checks).

Participant models:
- `GPT 5.2`
- `Claude-Sonnet-4.6`
- `GLM-5`
- `DeepSeek-V3.2`

Judge:
- `Gemini-3.1-Pro-Preview` as the non-participant judge (holistic pairwise verdict remains the canonical protocol).

## Current evidence files

Corrected main experiment and ordinal aggregation:
- `analysis/lit2test_corrected_gemini_main_results.md`
- `analysis/lit2test_corrected_gemini_main_results.json`
- `analysis/lit2test_expansion40_reverse_orientation_issue_and_recovery_20260721_zh.md`
- `outputs/lit2test_v02_expansion40_adjudicated40/pairwise_blind_reverse_correction65/correction_summary.md`

Construct validity and judge diagnostics:
- `analysis/lit2test_dimension_decomposed_gemini_audit_20260721.md`
- `analysis/lit2test_dimension_decomposed_gemini_audit_20260721.json`
- `analysis/lit2test_dimension_decomposed_gemini_case_level_20260721.csv`
- `analysis/lit2test_v02_same_source_rendering_bias_probe_gemini_summary.json`
- `analysis/lit2test_v02_gemini_naive_baseline_anchor_summary.json`

Human calibration:
- `analysis/lit2test_human_results_20260721_zh.md`

Manipulation checks:
- `analysis/lit2test_targeted_corruption_20x3_20260721.md`
- `analysis/lit2test_targeted_corruption_20x3_20260721.json`
- `analysis/lit2test_targeted_corruption_20x3_case_level_20260721.csv`
- `analysis/lit2test_targeted_subtle_corruption_20x3x2_sham_20260722.md`
- `analysis/lit2test_targeted_subtle_corruption_20x3x2_sham_20260722.json`
- `analysis/lit2test_targeted_subtle_corruption_case_level_20260722.csv`

Ablations and negative results (claim-bounding):
- `analysis/lit2test_v02_schema_freeform_prose_ablation_v2_summary.json`
- `analysis/lit2test_v02_falsifier_onoff_ablation_summary.json`

Data construction and provenance:
- `analysis/lit2test_v02_neighborhood_source_audit.json`

## Current headline results

- Corrected holistic main experiment: `2400/2400` ordered judgments, `1200/1200` folded cases, `950/250` stable/unstable; corrected BT and Condorcet preserve `GPT 5.2 > Claude-Sonnet-4.6 > GLM-5 > DeepSeek-V3.2`; the modal full ordering is recovered in all `10,000` case-bootstrap replicates.
- Dimension-decomposed audit: `188/188` valid judgments; structured overall agrees with holistic on `152/180` (`84.4%`), is order-consistent on `65/90` cases (`72.2%`), and selects the real answer on `8/8` hidden controls.
- Human calibration: `20` neighborhood cases, `90` real pairs, `4` hidden controls, `3` annotators; `34/39` (`87.2%`) decisive stable human majorities agree with corrected Gemini; human BT recovers the corrected ordering; agreement remains modest.
- Controlled clear single-field manipulation check: `120/120` valid judgments; clean answers win `40/40` ordered comparisons per target dimension; mean target-score drops `1.725` / `2.000` / `1.950`.
- Contrast-controlled subtle-corruption audit (`targeted_subtle_corruption_20x3x2_sham_v1`): `360/360` valid judgments; sham equivalence gate passes for all three dimensions (`0/40/0`, score diff `0.000`); case-level adjusted preference `0.550 [0.450, 0.650]` (grounding), `0.775 [0.662, 0.887]` (decisive metric), `0.537 [0.425, 0.650]` (falsifiability); pooled `0.621 [0.567, 0.679]`; interpretation gate: `supports_contrast_controlled_local_sensitivity`.
- Clean schema-vs-freeform ablation v2: `schema 122 : freeform 197 : tie 1`; schema is **not** a contribution claim.
- Clean falsifier on/off ablation: `with_falsifier 156 : no_falsifier 162 : tie 2`; falsifier is a harness/auditability constraint, not an observed holistic-quality gain.
- Gemini naive baseline anchor: `320/320` valid judgments; folded real-model stable wins `160/160`; naive stable wins `0`; flip-ties `0`.

## Superseded evidence (do not cite as current)

- `analysis/lit2test_v02_sonnet_full200_vs_3model_gemini_summary.json` — superseded by the corrected main results (pre-correction aggregation).
- `analysis/lit2test_v02_three_model_gemini_1200_summary.json` — superseded by the corrected main results (pre-correction aggregation).
- `analysis/lit2test_v02_human_calibration_mvp182_analysis.json` — superseded by `analysis/lit2test_human_results_20260721_zh.md`.
- `analysis/lit2test_v02_neighborhood_quality_audit_mvp40_analysis.json` — superseded by `analysis/lit2test_human_results_20260721_zh.md`.
- `archive/legacy_gpt_judge_20260711/` — archived GPT-judge era; historical diagnostics only.

## Rules

- Do not cite archived or superseded results as current paper evidence.
- Do not claim schema as a contribution; use schema as harness structure only.
- Do not use `accuracy` as shorthand for judge quality or objective idea quality.
- Do not claim a public leaderboard; this release supports paper reproduction only.
- Subtle-corruption claim boundary: the audit supports contrast-controlled local sensitivity to naturalistic targeted defects only; it is appendix/rebuttal-strength evidence under the frozen 20-case protocol and must not carry a main-text core claim, judge-accuracy claim, human-equivalence claim, or single-dimension causal claim.
- The 65-task reverse-orientation defect and its correction must be reported transparently in reproducibility or limitations discussion.
