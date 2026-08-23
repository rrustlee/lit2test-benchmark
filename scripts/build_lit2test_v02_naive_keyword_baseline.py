#!/usr/bin/env python3
"""Build a deterministic no-API naive keyword baseline for Lit2Test v0.2."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "lit2test_v02_naive_keyword_baseline"
OUT_JSONL = OUT_DIR / "generations_naive_keyword" / "lit2test_outputs.jsonl"
OUT_VALIDATED = OUT_DIR / "generations_naive_keyword" / "lit2test_outputs_validated.jsonl"
OUT_REPORT = OUT_DIR / "generations_naive_keyword" / "run_report.md"
OUT_REPORT_JSON = OUT_DIR / "generations_naive_keyword" / "run_report.json"
ANALYSIS_MD = ROOT / "analysis" / "lit2test_v02_naive_keyword_baseline_status_zh.md"
ANALYSIS_JSON = ROOT / "analysis" / "lit2test_v02_naive_keyword_baseline_status.json"

SOURCE_CONTEXT_FILES = {
    "expansion40": ROOT / "data" / "lit2test_v02_expansion40_adjudicated40_contexts.jsonl",
    "next40": ROOT / "data" / "lit2test_v02_next40_smallari_contexts.jsonl",
    "third40": ROOT / "data" / "lit2test_v02_third40_smallari_contexts.jsonl",
    "fourth40": ROOT / "data" / "lit2test_v02_fourth40_smallari_contexts.jsonl",
    "fifth40": ROOT / "data" / "lit2test_v02_fifth40_smallari_contexts.jsonl",
}

STOPWORDS = {
    "about",
    "across",
    "after",
    "against",
    "also",
    "and",
    "are",
    "because",
    "been",
    "between",
    "both",
    "can",
    "could",
    "does",
    "during",
    "each",
    "from",
    "have",
    "into",
    "its",
    "more",
    "not",
    "only",
    "paper",
    "papers",
    "propose",
    "proposed",
    "show",
    "shows",
    "such",
    "that",
    "the",
    "their",
    "these",
    "this",
    "through",
    "using",
    "with",
    "without",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def compact(text: Any, limit: int = 260) -> str:
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
            "The full method is not better than the supplied-paper baseline, the confidence intervals overlap across seeds, or the ablation/control performs similarly to the full method. "
            "This would weaken the claim that the proposed direction is a meaningful next-step research test."
        ),
        "model": "NaiveKeywordBaseline",
        "baseline_type": "deterministic_keyword_template_no_api",
        "source_policy": "lit2test_v02_naive_baseline_no_api_no_release_no_leaderboard",
    }


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    required = ["context_id", "condition", "literature_gap", "hypothesis", "minimal_test", "decisive_metric", "supporting_result", "falsifying_result"]
    flags = {
        "missing_required_field": any(not str(row.get(field, "")).strip() for field in required),
        "invalid_condition": row.get("condition") not in {"coherent_neighborhood", "random_same_area", "random_same_area_low_similarity", "broad_topic"},
        "weak_minimal_test": not re.search(r"compare|baseline|ablation|control|evaluate|dataset", row.get("minimal_test", ""), re.I),
        "weak_decisive_metric": not re.search(r"accuracy|auc|f1|score|metric|error|rate|performance|delta", row.get("decisive_metric", ""), re.I),
        "weak_falsifying_result": not re.search(r"not|similar|overlap|weaken|worse|same", row.get("falsifying_result", ""), re.I),
        "generic_gap": len(str(row.get("literature_gap", "")).split()) < 10,
    }
    errors = [name for name, value in flags.items() if value]
    return {**row, "schema_errors": [], "lit2test_valid": not errors, "lit2test_flags": flags, "lit2test_errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic Lit2Test naive keyword baseline")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    contexts: list[dict[str, Any]] = []
    per_batch: dict[str, int] = {}
    for batch, path in SOURCE_CONTEXT_FILES.items():
        rows = read_jsonl(path)
        contexts.extend(rows)
        per_batch[batch] = len(rows)
    if args.limit:
        contexts = contexts[: args.limit]

    rows = [build_baseline_row(context) for context in contexts]
    validated = [validate_row(row) for row in rows]
    write_jsonl(OUT_JSONL, rows)
    write_jsonl(OUT_VALIDATED, validated)
    valid_count = sum(1 for row in validated if row.get("lit2test_valid"))
    flag_counts: Counter[str] = Counter()
    for row in validated:
        for flag, value in row.get("lit2test_flags", {}).items():
            if value:
                flag_counts[flag] += 1

    report = {
        "status": "pass" if valid_count == len(validated) and len(validated) == (args.limit or 200) else "partial",
        "policy": "naive_keyword_baseline_no_api_no_release_no_leaderboard",
        "api_use": False,
        "baseline_model": "NaiveKeywordBaseline",
        "baseline_type": "deterministic_keyword_template_no_api",
        "contexts": len(contexts),
        "per_batch": per_batch,
        "output_file": rel(OUT_JSONL),
        "validated_output_file": rel(OUT_VALIDATED),
        "valid_rows": valid_count,
        "flagged_rows": len(validated) - valid_count,
        "flag_counts": dict(flag_counts),
        "intended_use_zh": "弱基线/下界：用于检查 Lit2Test 是否能区分模板化关键词拼接输出和真实模型科研构思，不用于公开排行榜。",
        "limitations_zh": "该 baseline 是模板生成，故意不具备真正创新能力；schema valid 不代表 idea 高质量。需要后续抽样 pairwise judge 或人类 anchor 比较。",
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
    }
    for path in [OUT_REPORT_JSON, ANALYSIS_JSON]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Lit2Test v0.2 Naive Keyword Baseline",
        "",
        "中文简介：这是一个完全 no-API 的弱基线。它从真实 context 的论文标题、贡献和 limitation 中抽关键词，填充 Lit2Test 6 字段输出，用来检验 harness 是否能区分模板化 proposal 和真实模型科研构思。它不是模型排名，不用于 leaderboard。",
        "",
        f"- Status: `{report['status']}`",
        f"- Policy: `{report['policy']}`",
        f"- API use: `{report['api_use']}`",
        f"- Baseline model: `{report['baseline_model']}`",
        f"- Contexts: `{report['contexts']}`",
        f"- Valid rows: `{report['valid_rows']}`",
        f"- Flagged rows: `{report['flagged_rows']}`",
        f"- Output: `{report['validated_output_file']}`",
        f"- Intended use: {report['intended_use_zh']}",
        f"- Limitations: {report['limitations_zh']}",
        f"- Release ready: `{report['release_ready']}`",
        f"- Allowed to publish leaderboard: `{report['allowed_to_publish_leaderboard']}`",
        "",
        "## Per Batch",
        "",
        "| Batch | Contexts |",
        "|---|---:|",
    ]
    lines.extend(f"| `{batch}` | {count} |" for batch, count in per_batch.items())
    lines.extend(["", "## Validation", "", f"- Flag counts: `{report['flag_counts']}`"])
    for path in [OUT_REPORT, ANALYSIS_MD]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Naive keyword baseline: {report['status']} valid={valid_count}/{len(validated)}")
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
