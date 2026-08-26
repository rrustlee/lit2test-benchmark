# Lit2Test: Code and Data Supplement

Code and data for the paper **[What Proves You Wrong: Benchmarking Language Models on Falsifiable Research Ideation](https://arxiv.org/abs/2608.22948)** (arXiv:2608.22948). This package contains the benchmark data, pipeline code, and frozen result artifacts supporting all quantitative claims in the paper.

## Package Layout

```
data/                   200 literature neighborhoods (5 batches x 40)
scripts/                Evaluation pipeline (generation -> judging -> aggregation)
scripts/plotting/       Figure reproduction
results/main/           Corrected main experiment (1,200 folded cases,
                        incl. both ordered verdicts per pair)
results/proposals/      All 800 six-field proposals (5 batches x 4 models)
results/robustness/     Tie-sensitivity + context-cluster bootstrap
results/diagnostics/    Corruption checks + dimension audit
results/second_judge/   Independent second-judge replication (2,400 judgments)
results/human_study/    Human calibration (protocol packages + results)
results/fig1_demo/      Figure 1 panel (a)/(b) illustration runs
survey/                 27-record related-work comparison matrix
```

## Offline Quick Start (no API key needed)

Requirements: Python 3.9+, `numpy`, `matplotlib` (for plotting only).

```bash
# 1. Verify the Table 1 Bradley-Terry values against the frozen artifact (instant)
python3 -c "import json; d=json.load(open('results/main/lit2test_corrected_gemini_main_results.json')); print(d['corrected']['folded']['bt_centered_log_ability'])"

# 2. Re-run the context-cluster bootstrap from raw folded cases (~30 s)
python3 scripts/run_context_cluster_bootstrap.py

# 3. Regenerate Figure 3 from frozen artifacts (~5 s)
python3 scripts/plotting/plot_figure3.py
```

Step 2 re-derives the Appendix C result (11--27% wider CIs, identical ranking) from
`results/main/corrected_folded_pairs.jsonl`; step 3 writes `figure3_rerun.{pdf,png}`
next to the script. Both were tested inside this package layout.

## Data

Each line of `data/lit2test_v02_*_smallari_contexts.jsonl` is one literature neighborhood:

- `context_id` — unique identifier (batch + topic slug)
- `research_context`, `open_problem`, `resource_constraint`, `task_instruction` — the exact text shown to participant models
- `papers` — four papers, each with `title`, `abstract`, `limitation` (reviewer-noted), and OpenReview `url`

All 800 papers are publicly available on OpenReview. No paper repeats across neighborhoods.

## Pipeline Stages (reproduction order)

All API scripts read the endpoint from `OPENAI_BASE_URL` and the key from `OPENAI_API_KEY`. Set both before running. Model identifiers used in the paper: GPT-5.2, Claude Sonnet 4.6, GLM-5, DeepSeek-V3.2 (participants); Gemini 3.1 Pro Preview (primary judge); Doubao Seed 2.0 Pro (second judge).

1. **Generation** — `scripts/run_lit2test_generations.py` (OpenAI-compatible) / `run_lit2test_generations_anthropic.py`. One six-field proposal per model per neighborhood; schema validation with bounded retries. Temperature 1.0, max tokens 1600.
2. **Pair construction + blind judging** — `scripts/run_lit2test_v02_pairwise.py` builds the 1,200 canonical pairs (deterministic A/B randomization by seed) and contains the verbatim judge prompt. `run_lit2test_v02_native_gemini_pairwise_judge.py` runs the judge in both presentation orders (2,400 ordered judgments).
3. **Folding + aggregation** — `scripts/aggregate_lit2test_v02_sonnet_full200_gemini.py` folds ordered pairs into order-stable/order-sensitive cases; `bootstrap_pairwise_rankings.py` runs the 10,000-replicate case bootstrap over Bradley-Terry fits.
4. **Diagnostics** — `run_lit2test_dimension_decomposed_gemini_audit.py` (structured per-dimension re-judging), `run_lit2test_targeted_corruption_20x3.py` + `analyze_lit2test_targeted_corruption_20x3.py` (clear manipulation check), `run_lit2test_subtle_corruption_20x3x2.py` + `analyze_lit2test_subtle_corruption.py` (subtle + sham audit), `build_lit2test_v02_naive_keyword_baseline.py` + `run_lit2test_v02_gemini_naive_baseline_anchor.py` (hidden controls).
5. **Robustness** — `run_context_cluster_bootstrap.py` (context-cluster bootstrap; Appendix C).
6. **Human study** — `aggregate_human_review.py` consumes annotation CSVs; the exact annotator-facing packages (bilingual protocol, rubric anchors, validator) are in `results/human_study/human_{practice,formal}_package.tar.gz`.

## Frozen Results (no API needed)

Every number in the paper can be re-derived from the frozen artifacts under `results/` without any API call:

| Paper claim | Artifact |
|---|---|
| Table 1 (BT, W-L-T, h2h, human WR) | `results/main/lit2test_corrected_gemini_main_results.json` |
| 950/250 fold + per-case outcomes | `results/main/corrected_folded_pairs.jsonl` |
| All 800 model proposals | `results/proposals/{batch}_{model}_proposals.jsonl` |
| Rendering control (RQ2) | `results/diagnostics/lit2test_v02_same_source_rendering_bias_probe_gemini_summary.json` |
| Hidden-control anchor (RQ2) | `results/diagnostics/lit2test_v02_gemini_naive_baseline_anchor_summary.json` |
| Dimension audit case level | `results/diagnostics/lit2test_dimension_decomposed_gemini_case_level_20260721.csv` |
| Tie sensitivity (RQ1) | `results/robustness/lit2test_tie_sensitivity_20260728.json` |
| Context-cluster bootstrap (RQ1, App. C) | `results/robustness/lit2test_context_cluster_bootstrap_20260729.json` |
| Manipulation checks (RQ2, Fig. 3a) | `results/diagnostics/lit2test_targeted_corruption_*.json` |
| Subtle + sham audit (RQ2, Fig. 3a-b) | `results/diagnostics/lit2test_targeted_subtle_corruption_*.json` |
| Dimension audit 84.4% (RQ2) | `results/diagnostics/lit2test_dimension_decomposed_gemini_audit_*.json` |
| Second judge (RQ1, App. E) | `results/second_judge/analysis.json` |
| Human calibration (RQ3, Fig. 3c) | `results/human_study/lit2test_human_results_20260721_zh.md` |
| Figure 1 panels (a)/(b) | `results/fig1_demo/` |
| 27-record survey (App. F) | `survey/related_work_comparison_matrix.csv` |

`results/main/CURRENT_EXPERIMENT_VERSION.md` is the authoritative index mapping every paper claim to its artifact.

## Figure Reproduction

`scripts/plotting/plot_figure3.py` regenerates Figure 3 from the frozen artifacts (adjust the four data paths at the top to point into `results/`).

## Citation

If you use this benchmark or data, please cite:

```bibtex
@article{wang2026lit2test,
  title   = {What Proves You Wrong: Benchmarking Language Models on Falsifiable Research Ideation},
  author  = {Wang, Ziyue and Yuan, Aomufei and Yao, Yiran and Yao, Linli and Zuo, Hongyao and Gong, Ziwen and Liu, Yuanxin and Li, Shicheng and Cai, Yishuo and Yang, Tong and Sun, Xu and Li, Xiaohui and Bai, Haoli},
  journal = {arXiv preprint arXiv:2608.22948},
  year    = {2026},
  url     = {https://arxiv.org/abs/2608.22948}
}
```

## License

- Code (`scripts/`): MIT License — see `LICENSE`.
- Data and result artifacts (`data/`, `results/`, `survey/`): CC BY 4.0 — see `LICENSE-DATA`. Paper abstracts and reviewer excerpts in `data/` derive from public ICLR submissions and CC BY 4.0 peer reviews on OpenReview; each record links to its source.

## Notes

- Each line of `results/main/corrected_folded_pairs.jsonl` carries BOTH ordered verdicts of its pair (`gemini_original_winner`, `gemini_reverse_winner`), so the 2,400-judgment ordered level, the folding rule, the ordered Bradley-Terry fit, and its case bootstrap can all be re-derived offline from this single file.
- Model identifiers in result artifacts (`Claude-Sonnet-4.6`, `Gemini-3.1-Pro-Preview`, etc.) correspond directly to the model names used in the paper.
- Table 1 prints DeepSeek-V3.2 BT as $-1.28$ (ordered-judgment fit); the stable-case fit in `results/main` gives $-1.27$. As stated in the Table 1 caption, the two fits agree within 0.01; all rankings and CIs are unaffected.
- The orientation defect in 65 reverse tasks of batch 1 and its correction are documented in `results/main/correction_summary.md`.
- Path placeholders `${PROJECT_ROOT}`, `${API_BASE_URL}`, `${API_HOST}` in scripts and archived logs replace environment-specific values.
- `results/human_study/lit2test_human_results_20260721_zh.md` is in Chinese (internal analysis report); all headline numbers it contains are reported in English in the paper and Appendix E.
