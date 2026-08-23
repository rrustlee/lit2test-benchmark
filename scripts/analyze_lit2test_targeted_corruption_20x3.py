#!/usr/bin/env python3
"""Aggregate the completed 20x3 targeted-corruption audit at case level."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from run_lit2test_dimension_decomposed_gemini_audit import validate_parsed


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs/lit2test_targeted_corruption_20x3"
DEFAULT_JSON = ROOT / "analysis/lit2test_targeted_corruption_20x3_20260721.json"
DEFAULT_MD = ROOT / "analysis/lit2test_targeted_corruption_20x3_20260721.md"
DEFAULT_CSV = ROOT / "analysis/lit2test_targeted_corruption_20x3_case_level_20260721.csv"
DIMENSIONS = ("grounding", "decisive_metric", "falsifiability")
ALL_SCORE_DIMENSIONS = ("grounding", "hypothesis_specificity", "minimality_feasibility", "decisive_metric", "falsifiability")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap(values: list[float], statistic: Callable[[np.ndarray], float], replicates: int, seed: int) -> list[float]:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(replicates, len(array)))
    samples = array[indices]
    estimates = np.asarray([statistic(sample) for sample in samples], dtype=float)
    return [float(x) for x in np.quantile(estimates, [0.025, 0.975])]


def summary_stat(values: list[float], replicates: int, seed: int) -> dict[str, Any]:
    return {
        "n_cases": len(values),
        "mean": float(statistics.mean(values)),
        "mean_ci95": bootstrap(values, lambda x: float(np.mean(x)), replicates, seed),
        "median": float(statistics.median(values)),
        "median_ci95": bootstrap(values, lambda x: float(np.median(x)), replicates, seed + 1),
        "bootstrap_unit": "canonical_case",
        "bootstrap_replicates": replicates,
    }


def side_value(item: dict[str, Any], side: str) -> Any:
    return item["score_a"] if side == "A" else item["score_b"]


def role_outcome(winner: str, task: dict[str, Any]) -> str:
    if winner == "tie":
        return "tie"
    role = task["role_a"] if winner == "A" else task["role_b"]
    return "clean" if role == "x" else "corrupt"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--md-output", default=str(DEFAULT_MD))
    parser.add_argument("--csv-output", default=str(DEFAULT_CSV))
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    json_output = Path(args.json_output).resolve()
    md_output = Path(args.md_output).resolve()
    csv_output = Path(args.csv_output).resolve()
    protocol = read_json(out / "protocol.json")
    completion = read_json(out / "completion_report.json")
    tasks = read_jsonl(out / "audit_tasks.jsonl")
    judgments = read_jsonl(out / "judgments.jsonl")
    task_map = {row["audit_id"]: row for row in tasks}
    errors: list[str] = []
    if completion.get("completion_gate_120") is not True:
        errors.append("completion_gate_120_not_pass")
    if len(tasks) != 120 or len(task_map) != 120:
        errors.append("expected_120_unique_tasks")
    if protocol.get("files", {}).get("audit_tasks_sha256") != sha256_file(out / "audit_tasks.jsonl"):
        errors.append("task_hash_mismatch")
    by_audit: dict[str, dict[str, Any]] = {}
    valid_counts: Counter[str] = Counter()
    for row in judgments:
        aid = row.get("audit_id")
        if aid not in task_map:
            errors.append(f"unknown_judgment:{aid}")
            continue
        validation = validate_parsed(row.get("judgment"), task_map[aid])
        if validation:
            errors.append(f"invalid_judgment:{aid}:{validation}")
            continue
        valid_counts[aid] += 1
        by_audit[aid] = row
    missing = sorted(set(task_map) - set(by_audit))
    if missing:
        errors.append(f"missing_valid_judgments:{len(missing)}")
    duplicates = {aid: count for aid, count in valid_counts.items() if count > 1}
    if duplicates:
        errors.append(f"duplicate_valid_judgments:{duplicates}")
    if errors:
        raise SystemExit("Integrity gate failed: " + "; ".join(errors))

    order_rows: list[dict[str, Any]] = []
    for aid, task in task_map.items():
        judgment = by_audit[aid]["judgment"]
        clean_side = "A" if task["role_a"] == "x" else "B"
        corrupt_side = "B" if clean_side == "A" else "A"
        target = task["target_dimension"]
        target_item = judgment["dimensions"][target]
        target_drop = float(side_value(target_item, clean_side) - side_value(target_item, corrupt_side))
        non_target_diffs = []
        for dim in ALL_SCORE_DIMENSIONS:
            if dim == target:
                continue
            item = judgment["dimensions"][dim]
            non_target_diffs.append(abs(float(side_value(item, clean_side) - side_value(item, corrupt_side))))
        order_rows.append({
            "audit_id": aid,
            "case_id": task["case_id"],
            "pair_id": task["pair_id"],
            "target_dimension": target,
            "order": task["order"],
            "overall_outcome": role_outcome(judgment["overall_winner"], task),
            "target_score_drop": target_drop,
            "non_target_absolute_score_drift": float(statistics.mean(non_target_diffs)),
            "clean_target_score": int(side_value(target_item, clean_side)),
            "corrupt_target_score": int(side_value(target_item, corrupt_side)),
        })

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in order_rows:
        grouped[(row["case_id"], row["target_dimension"])].append(row)
    case_rows: list[dict[str, Any]] = []
    for (case_id, target), rows in sorted(grouped.items()):
        rows.sort(key=lambda row: row["order"])
        if len(rows) != 2 or {row["order"] for row in rows} != {"original", "reverse"}:
            raise SystemExit(f"orientation mismatch for {case_id}/{target}")
        outcomes = [row["overall_outcome"] for row in rows]
        case_rows.append({
            "case_id": case_id,
            "target_dimension": target,
            "original_outcome": next(row["overall_outcome"] for row in rows if row["order"] == "original"),
            "reverse_outcome": next(row["overall_outcome"] for row in rows if row["order"] == "reverse"),
            "clean_overall_win_fraction": outcomes.count("clean") / 2.0,
            "corrupt_overall_win_fraction": outcomes.count("corrupt") / 2.0,
            "tie_fraction": outcomes.count("tie") / 2.0,
            "both_order_clean_win": outcomes.count("clean") == 2,
            "both_order_corrupt_win": outcomes.count("corrupt") == 2,
            "order_consistent": outcomes[0] == outcomes[1],
            "direct_flip": set(outcomes) == {"clean", "corrupt"},
            "target_score_drop": float(statistics.mean(row["target_score_drop"] for row in rows)),
            "non_target_absolute_score_drift": float(statistics.mean(row["non_target_absolute_score_drift"] for row in rows)),
        })
    if len(case_rows) != 60:
        raise SystemExit(f"expected 60 case/dimension rows, found {len(case_rows)}")

    summaries: dict[str, Any] = {}
    for dim_index, dimension in enumerate(DIMENSIONS):
        rows = [row for row in case_rows if row["target_dimension"] == dimension]
        ordered = [row for row in order_rows if row["target_dimension"] == dimension]
        win_values = [row["clean_overall_win_fraction"] for row in rows]
        drift_values = [row["non_target_absolute_score_drift"] for row in rows]
        drop_values = [row["target_score_drop"] for row in rows]
        summaries[dimension] = {
            "cases": len(rows),
            "ordered_judgments": len(ordered),
            "clean_overall_win_rate": {
                "clean_wins": sum(row["overall_outcome"] == "clean" for row in ordered),
                "denominator": len(ordered),
                "rate": float(statistics.mean(win_values)),
                "ci95": bootstrap(win_values, lambda x: float(np.mean(x)), 10000, 20260721 + dim_index * 100),
                "bootstrap_unit": "canonical_case",
            },
            "both_order_clean_win_count": sum(row["both_order_clean_win"] for row in rows),
            "both_order_corrupt_win_count": sum(row["both_order_corrupt_win"] for row in rows),
            "ordered_corrupt_wins": sum(row["overall_outcome"] == "corrupt" for row in ordered),
            "ordered_ties": sum(row["overall_outcome"] == "tie" for row in ordered),
            "target_score_drop": summary_stat(drop_values, 10000, 20260731 + dim_index * 100),
            "non_target_absolute_score_drift": summary_stat(drift_values, 10000, 20260741 + dim_index * 100),
            "order_consistency": {
                "consistent_cases": sum(row["order_consistent"] for row in rows),
                "cases": len(rows),
                "rate": sum(row["order_consistent"] for row in rows) / len(rows),
                "direct_flip_count": sum(row["direct_flip"] for row in rows),
                "tie_involved_mismatch_count": sum(not row["order_consistent"] and not row["direct_flip"] for row in rows),
            },
        }

    report = {
        "status": "complete",
        "protocol_id": protocol["protocol_id"],
        "policy": protocol["policy"],
        "judge_model": protocol["judge"]["model"],
        "completion_gate": {"tasks": 120, "valid": len(by_audit), "canonical_cases": 20, "canonical_pairs": 60},
        "aggregation": {"unit": "canonical_case", "bootstrap_replicates": 10000, "confidence_weighting": False, "ordered_rows_as_independent_samples": False},
        "dimensions": summaries,
        "claim_boundary": protocol["claim_boundary"],
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
        "artifacts": {"protocol_sha256": sha256_file(out / "protocol.json"), "tasks_sha256": sha256_file(out / "audit_tasks.jsonl"), "judgments_sha256": sha256_file(out / "judgments.jsonl")},
    }
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(case_rows[0]))
        writer.writeheader()
        writer.writerows(case_rows)
    lines = [
        "# Lit2Test Targeted Corruption Audit（20×3×2）",
        "",
        "本实验只支持 `localized counterfactual judge sensitivity`：它检查固定答案中单字段缺陷是否被 Gemini 的对应维度察觉，不是人类 gold label、生成质量实验或 leaderboard。",
        "",
        f"- Status: `{report['status']}`",
        "- Valid judgments: `120/120`",
        "- Canonical cases: `20`",
        "- Canonical pairs: `60`",
        "- Bootstrap: `10,000` case-level replicates",
        "- Confidence weighting: `False`",
        "",
        "## Results",
        "",
        "| Target dimension | Clean overall wins | Both-order clean wins | Target drop, mean [95% CI] | Target drop, median [95% CI] | Non-target abs drift, mean [95% CI] | Order consistency | Direct flips | Corrupt wins | Ties |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dimension in DIMENSIONS:
        item = summaries[dimension]
        win = item["clean_overall_win_rate"]
        drop = item["target_score_drop"]
        drift = item["non_target_absolute_score_drift"]
        order = item["order_consistency"]
        lines.append(
            f"| `{dimension}` | {win['clean_wins']}/{win['denominator']} ({win['rate']:.3f}) | "
            f"{item['both_order_clean_win_count']}/20 | {drop['mean']:.3f} [{drop['mean_ci95'][0]:.3f}, {drop['mean_ci95'][1]:.3f}] | "
            f"{drop['median']:.3f} [{drop['median_ci95'][0]:.3f}, {drop['median_ci95'][1]:.3f}] | "
            f"{drift['mean']:.3f} [{drift['mean_ci95'][0]:.3f}, {drift['mean_ci95'][1]:.3f}] | "
            f"{order['consistent_cases']}/{order['cases']} ({order['rate']:.3f}) | {order['direct_flip_count']} | "
            f"{item['ordered_corrupt_wins']} | {item['ordered_ties']} |"
        )
    lines.extend([
        "",
        "## Claim Boundary",
        "",
        "允许表述：该局部反事实审计检验 judge 是否对单个 rubric dimension 的定向缺陷敏感。若对应分数下降且非目标维度漂移较小，可称为 dimension-specific local sensitivity。",
        "",
        "禁止据此声称 schema 提升生成 idea、falsifier 要求改善科研结果、Gemini 等于客观科研质量、falsifiability 必然最有区分力，或 Lit2Test 已获得 benchmark-wide human validation。",
    ])
    md_output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "valid": len(by_audit), "results": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
