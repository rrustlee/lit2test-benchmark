#!/usr/bin/env python3
"""Prepare and summarize the current Gemini naive-baseline sanity check.

#13 goal: verify that the current Gemini judge + Lit2Test harness is not
fooled by schema-valid keyword/template answers.

This script intentionally writes to a new current-experiment output root:
outputs/lit2test_v02_gemini_naive_baseline_anchor/
It does not reuse the archived GPT-judge naive-baseline artifacts.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "outputs" / "lit2test_v02_gemini_naive_baseline_anchor"
GEN_DIR = OUT_ROOT / "generations_naive_keyword"
PAIRWISE = OUT_ROOT / "pairwise_blind"
PAIRWISE_REV = OUT_ROOT / "pairwise_blind_reverse"
NAIVE_JSONL = GEN_DIR / "lit2test_outputs.jsonl"
NAIVE_VALIDATED = GEN_DIR / "lit2test_outputs_validated.jsonl"
TASKS = PAIRWISE / "pairwise_tasks.jsonl"
TASKS_REV = PAIRWISE_REV / "pairwise_tasks.jsonl"
PREP_JSON = ROOT / "analysis" / "lit2test_v02_gemini_naive_baseline_anchor_prep.json"
PREP_MD = ROOT / "analysis" / "lit2test_v02_gemini_naive_baseline_anchor_prep.md"
SUMMARY_JSON = ROOT / "analysis" / "lit2test_v02_gemini_naive_baseline_anchor_summary.json"
SUMMARY_MD = ROOT / "analysis" / "lit2test_v02_gemini_naive_baseline_anchor_summary.md"

BATCHES = {
    "expansion40": {
        "context_file": ROOT / "data" / "lit2test_v02_expansion40_adjudicated40_contexts.jsonl",
        "output_dir": ROOT / "outputs" / "lit2test_v02_expansion40_full",
    },
    "next40": {
        "context_file": ROOT / "data" / "lit2test_v02_next40_smallari_contexts.jsonl",
        "output_dir": ROOT / "outputs" / "lit2test_v02_next40_full",
    },
    "third40": {
        "context_file": ROOT / "data" / "lit2test_v02_third40_smallari_contexts.jsonl",
        "output_dir": ROOT / "outputs" / "lit2test_v02_third40_full",
    },
    "fourth40": {
        "context_file": ROOT / "data" / "lit2test_v02_fourth40_smallari_contexts.jsonl",
        "output_dir": ROOT / "outputs" / "lit2test_v02_fourth40_full",
    },
    "fifth40": {
        "context_file": ROOT / "data" / "lit2test_v02_fifth40_smallari_contexts.jsonl",
        "output_dir": ROOT / "outputs" / "lit2test_v02_fifth40_full",
    },
}

MODELS = {
    "GPT 5.2": "generations_gpt52",
    "Claude-Sonnet-4.6": "generations_sonnet46",
    "GLM-5": "generations_glm5",
    "DeepSeek-V3.2": "generations_deepseek_v32",
}

STOPWORDS = {
    "about", "across", "after", "against", "also", "and", "are", "because", "been", "between", "both",
    "can", "could", "does", "during", "each", "from", "have", "into", "its", "more", "not", "only",
    "paper", "papers", "propose", "proposed", "show", "shows", "such", "that", "the", "their", "these",
    "this", "through", "using", "with", "without",
}

REQUIRED_FIELDS = [
    "context_id",
    "condition",
    "literature_gap",
    "hypothesis",
    "minimal_test",
    "decisive_metric",
    "supporting_result",
    "falsifying_result",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def safe_model_id(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model).strip("_")


def compact(text: Any, limit: int = 220) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def words(text: str) -> list[str]:
    return [item.lower() for item in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text)]


def top_terms(context: dict[str, Any], n: int = 6) -> list[str]:
    pool_metadata = context.get("pool_metadata", {}) if isinstance(context.get("pool_metadata"), dict) else {}
    metadata_terms = [str(term) for term in pool_metadata.get("top_terms", []) if str(term).strip()]
    if metadata_terms:
        return metadata_terms[:n]
    text = " ".join(
        " ".join(str(paper.get(key, "")) for key in ["title", "abstract", "key_contribution", "limitation"])
        for paper in context.get("papers", [])
    )
    counts = Counter(word for word in words(text) if word not in STOPWORDS and len(word) > 3)
    return [term for term, _ in counts.most_common(n)] or ["method", "evaluation", "baseline"]


def pick_papers(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    papers = context.get("papers", [])
    if not papers:
        return {}, {}
    accepted = [paper for paper in papers if "accept" in str(paper.get("decision", "")).lower()]
    rejected = [paper for paper in papers if "reject" in str(paper.get("decision", "")).lower()]
    first = accepted[0] if accepted else papers[0]
    second = rejected[0] if rejected else (papers[1] if len(papers) > 1 else papers[0])
    return first, second


def build_baseline_row(context: dict[str, Any]) -> dict[str, Any]:
    first, second = pick_papers(context)
    terms = top_terms(context)
    area = first.get("primary_area") or context.get("field") or "the supplied neighborhood"
    first_title = compact(first.get("title", "paper A"), 120)
    second_title = compact(second.get("title", "paper B"), 120)
    first_signal = compact(first.get("key_contribution") or first.get("important_result") or first.get("abstract"), 220)
    second_limit = compact(second.get("limitation") or second.get("important_result") or second.get("abstract"), 220)
    term_text = ", ".join(terms[:4])
    return {
        "context_id": context.get("context_id"),
        "condition": context.get("condition"),
        "literature_gap": (
            f"The supplied neighborhood around {area} contains related work on {term_text}. "
            f"A simple unresolved gap is that {first_title} reports a useful method or result ({first_signal}), "
            f"while {second_title} highlights a limitation or adjacent setting ({second_limit}). "
            "The naive baseline therefore proposes a direct cross-paper comparison rather than a new mechanism."
        ),
        "hypothesis": (
            f"If the method or claim from {first_title} generalizes to the setting suggested by {second_title}, "
            "then it should outperform a standard baseline on the same public data under matched compute; otherwise the apparent gap is mostly dataset- or setting-specific."
        ),
        "minimal_test": (
            f"Implement or reuse the main method/baseline from {first_title} and compare it with a simple baseline from the supplied papers on one public dataset relevant to {term_text}. "
            "Run one ablation/control that removes the key claimed component, keep train/test splits and compute fixed, and evaluate the same setup across three random seeds within the stated resource budget."
        ),
        "decisive_metric": (
            "Primary metric: task performance score such as accuracy/F1/AUC or error rate on the public test set, plus the gap to the supplied-paper baseline. "
            "Secondary diagnostic: ablation delta between the full method and the component-removed control, reported with mean and standard deviation across seeds."
        ),
        "supporting_result": (
            "The full method beats the supplied-paper baseline by a clear margin on the primary metric, and the component-removal ablation loses most of that gain while compute and data are matched."
        ),
        "falsifying_result": (
            f"The hypothesis would be weakened if the method or claim adapted from {first_title} does not outperform the baseline or setting associated with {second_title} "
            "on the decisive metric under matched compute and data; if results overlap across seeds; or if the ablation/control performs similarly to the full method. "
            "This would indicate that the proposed cross-paper connection is not a meaningful or decisive next-step test."
        ),
        "model": "NaiveKeywordBaseline",
        "baseline_type": "deterministic_keyword_template_no_api",
        "source_policy": "lit2test_v02_gemini_naive_baseline_anchor_no_release_no_leaderboard",
    }


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    flags = {
        "missing_required_field": any(not str(row.get(field, "")).strip() for field in REQUIRED_FIELDS),
        "invalid_condition": row.get("condition") not in {"coherent_neighborhood", "random_same_area", "random_same_area_low_similarity", "broad_topic"},
        "weak_minimal_test": not re.search(r"compare|baseline|ablation|control|evaluate|dataset", row.get("minimal_test", ""), re.I),
        "weak_decisive_metric": not re.search(r"accuracy|auc|f1|score|metric|error|rate|performance|delta", row.get("decisive_metric", ""), re.I),
        "weak_falsifying_result": not re.search(r"weakened|does not outperform|overlap|similarly|not a meaningful|not.*decisive", row.get("falsifying_result", ""), re.I),
        "generic_gap": len(str(row.get("literature_gap", "")).split()) < 10,
    }
    errors = [name for name, value in flags.items() if value]
    return {**row, "schema_errors": [], "lit2test_valid": not errors, "lit2test_flags": flags, "lit2test_errors": errors}


def compact_answer(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in ["literature_gap", "hypothesis", "minimal_test", "decisive_metric", "supporting_result", "falsifying_result"]}


def compact_context(context: dict[str, Any]) -> dict[str, Any]:
    papers = []
    for paper in context.get("papers", []):
        papers.append({key: paper.get(key) for key in ["title", "abstract", "key_contribution", "limitation", "important_result"]})
    return {
        "context_id": context.get("context_id"),
        "field": context.get("field"),
        "research_context": context.get("research_context"),
        "open_problem": context.get("open_problem"),
        "resource_constraint": context.get("resource_constraint"),
        "papers": papers,
    }


def load_by_context(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["context_id"]): row for row in read_jsonl(path)}


def latest_valid_by_pair(path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], int]:
    raw: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_rows = 0
    for row in read_jsonl(path):
        raw_rows += 1
        if row.get("pair_id"):
            raw[str(row["pair_id"])].append(row)
    latest: dict[str, dict[str, Any]] = {}
    fatal_rows: list[dict[str, Any]] = []
    for pair_id, rows in raw.items():
        valid = [row for row in rows if row.get("winner") in {"A", "B", "tie"} and not row.get("judge_errors")]
        if valid:
            latest[pair_id] = valid[-1]
        else:
            fatal_rows.append(rows[-1])
    return latest, fatal_rows, raw_rows


def usable_arm(row: dict[str, Any], model: str) -> str:
    if row.get("winner") == "tie":
        return "tie"
    winner = row.get("winning_system")
    if winner == "NaiveKeywordBaseline":
        return "naive"
    if winner == model:
        return "model"
    return "invalid"


def prepare(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    contexts_by_batch: dict[str, list[dict[str, Any]]] = {}
    contexts_by_id: dict[str, dict[str, Any]] = {}
    per_batch_contexts: dict[str, int] = {}
    for batch, info in BATCHES.items():
        rows = read_jsonl(info["context_file"])
        contexts_by_batch[batch] = rows
        per_batch_contexts[batch] = len(rows)
        for row in rows:
            contexts_by_id[str(row["context_id"])] = row

    naive_rows = [build_baseline_row(context) for batch in BATCHES for context in contexts_by_batch[batch]]
    naive_validated = [validate_row(row) for row in naive_rows]
    write_jsonl(NAIVE_JSONL, naive_rows)
    write_jsonl(NAIVE_VALIDATED, naive_validated)
    naive_by_context = {str(row["context_id"]): row for row in naive_validated}

    model_outputs: dict[str, dict[str, dict[str, Any]]] = {model: {} for model in MODELS}
    output_counts: dict[str, dict[str, int]] = {model: {} for model in MODELS}
    for model, gen_dir in MODELS.items():
        for batch, info in BATCHES.items():
            path = info["output_dir"] / gen_dir / "lit2test_outputs_validated.jsonl"
            rows = read_jsonl(path)
            output_counts[model][batch] = len(rows)
            for row in rows:
                model_outputs[model][str(row["context_id"])] = row

    selected: list[tuple[str, str]] = []
    eligible_by_batch: dict[str, int] = {}
    for batch, rows in contexts_by_batch.items():
        eligible = []
        for row in rows:
            context_id = str(row["context_id"])
            if context_id not in naive_by_context:
                continue
            if all(context_id in model_outputs[model] for model in MODELS):
                eligible.append(context_id)
        eligible_by_batch[batch] = len(eligible)
        if len(eligible) < args.per_batch:
            raise SystemExit(f"Not enough eligible contexts for {batch}: {len(eligible)} < {args.per_batch}")
        for context_id in rng.sample(eligible, args.per_batch):
            selected.append((batch, context_id))

    tasks = []
    for batch, context_id in selected:
        context = contexts_by_id[context_id]
        naive = naive_by_context[context_id]
        for model in MODELS:
            model_row = model_outputs[model][context_id]
            model_first = rng.choice([True, False])
            if model_first:
                system_a, answer_a = model, model_row
                system_b, answer_b = "NaiveKeywordBaseline", naive
            else:
                system_a, answer_a = "NaiveKeywordBaseline", naive
                system_b, answer_b = model, model_row
            tasks.append({
                "pair_id": f"{context_id}__NaiveKeywordBaseline__vs__{safe_model_id(model)}",
                "context_id": context_id,
                "base_topic_id": context.get("base_topic_id"),
                "field": context.get("field"),
                "batch": batch,
                "system_a": system_a,
                "system_b": system_b,
                "canonical_system_x": "NaiveKeywordBaseline",
                "canonical_system_y": model,
                "answer_a": compact_answer(answer_a),
                "answer_b": compact_answer(answer_b),
                "context": compact_context(context),
                "source_policy": "gemini_naive_baseline_anchor_no_release_no_leaderboard",
            })

    reverse = []
    for task in tasks:
        reverse.append({
            **task,
            "system_a": task["system_b"],
            "system_b": task["system_a"],
            "answer_a": task["answer_b"],
            "answer_b": task["answer_a"],
        })

    write_jsonl(TASKS, tasks)
    write_jsonl(TASKS_REV, reverse)

    flag_counts: Counter[str] = Counter()
    for row in naive_validated:
        for flag, value in row.get("lit2test_flags", {}).items():
            if value:
                flag_counts[flag] += 1

    report = {
        "status": "pass" if len(tasks) == args.per_batch * len(BATCHES) * len(MODELS) and not flag_counts else "partial",
        "policy": "gemini_naive_baseline_anchor_prep_no_api_no_release_no_leaderboard",
        "api_use": False,
        "seed": args.seed,
        "per_batch": args.per_batch,
        "baseline_model": "NaiveKeywordBaseline",
        "baseline_type": "deterministic_keyword_template_no_api",
        "falsifying_result_template": "The hypothesis would be weakened if the method or claim adapted from {paper_a_title} does not outperform the baseline or setting associated with {paper_b_title} on the decisive metric under matched compute and data; if results overlap across seeds; or if the ablation/control performs similarly to the full method. This would indicate that the proposed cross-paper connection is not a meaningful or decisive next-step test.",
        "contexts_total": len(naive_validated),
        "naive_valid_rows": sum(1 for row in naive_validated if row.get("lit2test_valid")),
        "flag_counts": dict(flag_counts),
        "per_batch_contexts": per_batch_contexts,
        "eligible_by_batch": eligible_by_batch,
        "selected_contexts": [{"batch": batch, "context_id": context_id} for batch, context_id in selected],
        "models": list(MODELS),
        "model_output_counts": output_counts,
        "pairwise_tasks": len(tasks),
        "reverse_tasks": len(reverse),
        "expected_pairs": args.per_batch * len(BATCHES) * len(MODELS),
        "expected_judgments": args.per_batch * len(BATCHES) * len(MODELS) * 2,
        "output_files": {
            "naive_validated": rel(NAIVE_VALIDATED),
            "tasks": rel(TASKS),
            "reverse_tasks": rel(TASKS_REV),
        },
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
    }
    write_json(PREP_JSON, report)

    lines = [
        "# #13 Gemini Naive Baseline Anchor Prep",
        "",
        "中文简介：当前 Gemini+4 口径的模板弱基线 sanity check 准备结果。该实验检查 Gemini judge 是否会被 schema-valid 的关键词模板答案糊弄。旧 GPT judge naive baseline 已归档，本实验使用新输出路径。",
        "",
        f"- Status: `{report['status']}`",
        f"- Policy: `{report['policy']}`",
        f"- API use: `{report['api_use']}`",
        f"- Seed: `{args.seed}`",
        f"- Baseline: `{report['baseline_model']}`",
        f"- Contexts total: `{report['contexts_total']}`",
        f"- Naive valid rows: `{report['naive_valid_rows']}`",
        f"- Pairwise tasks: `{report['pairwise_tasks']}` + reverse `{report['reverse_tasks']}`",
        f"- Expected Gemini judgments: `{report['expected_judgments']}`",
        f"- Tasks: `{report['output_files']['tasks']}`",
        f"- Reverse tasks: `{report['output_files']['reverse_tasks']}`",
        "",
        "## Selected contexts",
        "",
        "| Batch | Count |",
        "|---|---:|",
    ]
    selected_counts = Counter(batch for batch, _ in selected)
    for batch in BATCHES:
        lines.append(f"| `{batch}` | {selected_counts[batch]} |")
    lines.extend(["", "## Falsifying-result template", "", report["falsifying_result_template"]])
    PREP_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"prep status={report['status']} tasks={len(tasks)} reverse={len(reverse)} expected_judgments={report['expected_judgments']}")


def summarize(_: argparse.Namespace) -> None:
    tasks = {str(row["pair_id"]): row for row in read_jsonl(TASKS)}
    reverse_tasks = {str(row["pair_id"]): row for row in read_jsonl(TASKS_REV)}
    blind, blind_fatal, blind_raw = latest_valid_by_pair(PAIRWISE / "judges_gemini" / "pairwise_judgments.jsonl")
    reverse, reverse_fatal, reverse_raw = latest_valid_by_pair(PAIRWISE_REV / "judges_gemini" / "pairwise_judgments.jsonl")

    cases: list[dict[str, Any]] = []
    missing: list[str] = []
    for pair_id, task in sorted(tasks.items()):
        model = str(task.get("canonical_system_y"))
        b = blind.get(pair_id)
        r = reverse.get(pair_id)
        if not b or not r:
            missing.append(pair_id)
            continue
        blind_arm = usable_arm(b, model)
        reverse_arm = usable_arm(r, model)
        if blind_arm == "model" and reverse_arm == "model":
            folded = "real_stable_win"
        elif blind_arm == "naive" and reverse_arm == "naive":
            folded = "naive_stable_win"
        elif blind_arm == "tie" and reverse_arm == "tie":
            folded = "judge_tie"
        else:
            folded = "flip_tie"
        cases.append({
            "pair_id": pair_id,
            "context_id": task.get("context_id"),
            "batch": task.get("batch"),
            "model": model,
            "blind_arm": blind_arm,
            "reverse_arm": reverse_arm,
            "folded": folded,
            "blind_winner_side": b.get("winner"),
            "reverse_winner_side": r.get("winner"),
            "blind_confidence": b.get("confidence"),
            "reverse_confidence": r.get("confidence"),
        })

    order_rows = []
    for order_name, data in [("blind", blind), ("reverse", reverse)]:
        for pair_id, row in data.items():
            task = tasks.get(pair_id) or reverse_tasks.get(pair_id)
            if not task:
                continue
            model = str(task.get("canonical_system_y"))
            order_rows.append({
                "order": order_name,
                "pair_id": pair_id,
                "batch": task.get("batch"),
                "model": model,
                "arm": usable_arm(row, model),
                "winner_side": row.get("winner"),
                "confidence": row.get("confidence"),
            })

    folded_counts = Counter(row["folded"] for row in cases)
    order_arm_counts = Counter(row["arm"] for row in order_rows)
    side_counts = Counter(row["winner_side"] for row in order_rows)
    confidence_counts = Counter(str(row["confidence"]) for row in order_rows)

    by_model: dict[str, Any] = {}
    for model in MODELS:
        rows = [row for row in cases if row["model"] == model]
        by_model[model] = {
            "pairs": len(rows),
            "folded": dict(Counter(row["folded"] for row in rows)),
            "order_level": dict(Counter(row["arm"] for row in order_rows if row["model"] == model)),
        }

    by_batch: dict[str, Any] = {}
    for batch in BATCHES:
        rows = [row for row in cases if row["batch"] == batch]
        by_batch[batch] = {
            "pairs": len(rows),
            "folded": dict(Counter(row["folded"] for row in rows)),
            "order_level": dict(Counter(row["arm"] for row in order_rows if row["batch"] == batch)),
        }

    valid_order_rows = len(order_rows)
    real_order_wins = order_arm_counts["model"]
    real_order_rate = round(real_order_wins / valid_order_rows, 4) if valid_order_rows else 0.0
    expected_pairs = len(tasks)
    expected_judgments = len(tasks) + len(reverse_tasks)
    checks = {
        "tasks_160": len(tasks) == 160 and len(reverse_tasks) == 160,
        "valid_judgments_320": valid_order_rows == 320,
        "no_missing_pairs": not missing,
        "naive_stable_win_0": folded_counts["naive_stable_win"] == 0,
        "real_stable_win_ge_152": folded_counts["real_stable_win"] >= 152,
        "order_level_real_win_rate_ge_0_95": real_order_rate >= 0.95,
    }
    acceptable_checks = {
        "valid_judgments_ge_316": valid_order_rows >= 316,
        "naive_stable_win_le_1": folded_counts["naive_stable_win"] <= 1,
        "real_stable_win_ge_144": folded_counts["real_stable_win"] >= 144,
    }
    strong_pass = all(checks.values())
    acceptable_pass = all(acceptable_checks.values())
    status = "pass" if strong_pass else "acceptable_pass" if acceptable_pass else "fail"

    report = {
        "status": status,
        "policy": "gemini_naive_baseline_anchor_no_release_no_leaderboard",
        "api_use": True,
        "judge": "Gemini-3.1-Pro-Preview (non-participant)",
        "experiment": "#13 real model outputs vs schema-valid NaiveKeywordBaseline, 40 contexts x 4 models x 2 order",
        "task_file": rel(TASKS),
        "reverse_task_file": rel(TASKS_REV),
        "judgment_files": [
            rel(PAIRWISE / "judges_gemini" / "pairwise_judgments.jsonl"),
            rel(PAIRWISE_REV / "judges_gemini" / "pairwise_judgments.jsonl"),
        ],
        "tasks": len(tasks),
        "reverse_tasks": len(reverse_tasks),
        "expected_pairs": expected_pairs,
        "expected_judgments": expected_judgments,
        "raw_rows": {"blind": blind_raw, "reverse": reverse_raw},
        "valid_latest_rows": {"blind": len(blind), "reverse": len(reverse), "combined": valid_order_rows},
        "fatal_latest_rows": {"blind": len(blind_fatal), "reverse": len(reverse_fatal)},
        "pairs_compared": len(cases),
        "folded_counts": dict(folded_counts),
        "order_level_arm_counts": dict(order_arm_counts),
        "order_level_real_win_rate": real_order_rate,
        "side_counts": dict(side_counts),
        "confidence_counts": dict(confidence_counts),
        "by_model": by_model,
        "by_batch": by_batch,
        "missing_pairs": missing,
        "checks_strong_pass": checks,
        "checks_acceptable_pass": acceptable_checks,
        "cases": cases,
        "interpretation_zh": (
            "#13 Gemini naive baseline sanity check: schema-valid 的 NaiveKeywordBaseline 只是关键词/模板拼接，"
            "用于验证当前 Gemini judge + Lit2Test harness 是否会被字段齐全但内容浅的答案糊弄。"
            "若真实模型在正反序 folded 口径下稳定获胜，说明 judge 不是只看 schema/关键词。"
        ),
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
    }
    write_json(SUMMARY_JSON, report)

    lines = [
        "# #13 Gemini Naive Baseline Anchor Summary",
        "",
        "中文简介：当前 Gemini+4 口径下的 naive baseline sanity check。NaiveKeywordBaseline 是 schema-valid 的 deterministic keyword/template baseline；本实验检查 Gemini judge 是否会被这种模板答案糊弄。",
        "",
        f"- Status: `{status}`",
        f"- Policy: `{report['policy']}`",
        f"- Judge: `{report['judge']}`",
        f"- Valid latest rows: `{valid_order_rows}` / `{expected_judgments}`",
        f"- Pairs compared: `{len(cases)}` / `{expected_pairs}`",
        f"- Folded real stable wins: `{folded_counts['real_stable_win']}`",
        f"- Folded naive stable wins: `{folded_counts['naive_stable_win']}`",
        f"- Folded flip ties: `{folded_counts['flip_tie']}`",
        f"- Folded judge ties: `{folded_counts['judge_tie']}`",
        f"- Order-level real win rate: `{real_order_rate}`",
        f"- Release ready: `{report['release_ready']}`",
        f"- Allowed to publish leaderboard: `{report['allowed_to_publish_leaderboard']}`",
        "",
        "## By model",
        "",
        "| Model | Pairs | Real stable win | Naive stable win | Flip tie | Judge tie | Order-level model wins | Order-level naive wins |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, item in by_model.items():
        folded = Counter(item["folded"])
        order_level = Counter(item["order_level"])
        lines.append(
            f"| `{model}` | {item['pairs']} | {folded['real_stable_win']} | {folded['naive_stable_win']} | "
            f"{folded['flip_tie']} | {folded['judge_tie']} | {order_level['model']} | {order_level['naive']} |"
        )
    lines.extend([
        "",
        "## By batch",
        "",
        "| Batch | Pairs | Real stable win | Naive stable win | Flip tie | Judge tie |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for batch, item in by_batch.items():
        folded = Counter(item["folded"])
        lines.append(
            f"| `{batch}` | {item['pairs']} | {folded['real_stable_win']} | {folded['naive_stable_win']} | {folded['flip_tie']} | {folded['judge_tie']} |"
        )
    lines.extend(["", "## Checks", ""])
    lines.extend(f"- `{name}`: `{value}`" for name, value in checks.items())
    lines.extend(["", "## Interpretation", "", report["interpretation_zh"]])
    SUMMARY_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(
        "summary "
        f"status={status} valid={valid_order_rows}/{expected_judgments} "
        f"real_stable={folded_counts['real_stable_win']} naive_stable={folded_counts['naive_stable_win']} "
        f"flip_tie={folded_counts['flip_tie']} real_order_rate={real_order_rate}"
    )
    if status == "fail":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare/summarize #13 Gemini naive baseline sanity check")
    sub = parser.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--per-batch", type=int, default=8)
    prep.add_argument("--seed", type=int, default=20260711)
    prep.set_defaults(func=prepare)
    summ = sub.add_parser("summarize")
    summ.set_defaults(func=summarize)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
