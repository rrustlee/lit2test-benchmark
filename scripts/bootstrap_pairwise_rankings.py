#!/usr/bin/env python3
"""Bootstrap uncertainty diagnostics for IdeaBench pairwise rankings."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALID_CHOICES = {"A", "B", "tie"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def winner_from_judge(row: dict[str, Any]) -> str | None:
    judgment = row.get("judgment")
    if not judgment:
        return None
    winner = str(judgment.get("winner", "")).strip()
    return winner if winner in VALID_CHOICES else None


def load_judge_preferences(paths: list[str]) -> list[dict[str, str]]:
    prefs: list[dict[str, str]] = []
    for path_value in paths:
        path = Path(path_value)
        for row in read_jsonl(path):
            winner = winner_from_judge(row)
            if winner:
                prefs.append({"pair_id": row["pair_id"], "winner": winner, "source": f"judge:{path.name}:{row.get('judge_id', '')}"})
    return prefs


def load_human_majority_preferences(path_value: str, pairs: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for row in read_csv(Path(path_value)):
        pair_id = row.get("pair_id", "").strip()
        choice = row.get("choice", "").strip()
        if pair_id in pairs and choice in VALID_CHOICES:
            votes[pair_id][choice] += 1
    prefs: list[dict[str, str]] = []
    for pair_id, counts in votes.items():
        top = counts.most_common()
        if not top:
            continue
        winner = "tie" if len(top) > 1 and top[0][1] == top[1][1] else top[0][0]
        prefs.append({"pair_id": pair_id, "winner": winner, "source": f"human_majority:{Path(path_value).name}"})
    return prefs


def system_points(pair: dict[str, Any], winner: str) -> tuple[float, float]:
    if winner == "A":
        return 1.0, 0.0
    if winner == "B":
        return 0.0, 1.0
    return 0.5, 0.5


def records_from_prefs(pairs: dict[str, dict[str, Any]], prefs: list[dict[str, str]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for pref in prefs:
        pair = pairs.get(pref["pair_id"])
        if not pair:
            continue
        records.append(
            {
                "pair_id": pref["pair_id"],
                "topic_id": pair["topic_id"],
                "system_a_id": pair["system_a_id"],
                "system_b_id": pair["system_b_id"],
                "winner": pref["winner"],
                "source": pref["source"],
            }
        )
    return records


def score_rates(records: list[dict[str, Any]], systems: list[str]) -> dict[str, float | None]:
    points = {system: 0.0 for system in systems}
    counts = {system: 0 for system in systems}
    for row in records:
        a = row["system_a_id"]
        b = row["system_b_id"]
        a_score, b_score = system_points(row, row["winner"])
        points[a] += a_score
        points[b] += b_score
        counts[a] += 1
        counts[b] += 1
    return {system: (points[system] / counts[system] if counts[system] else None) for system in systems}


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = (len(values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return values[lo] * (1 - frac) + values[hi] * frac


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap IdeaBench pairwise ranking uncertainty")
    parser.add_argument("--pairs", required=True)
    parser.add_argument("--judge", action="append", default=[])
    parser.add_argument("--human-responses", default="")
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--title", default="IdeaBench Pairwise Bootstrap Uncertainty Report")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json-output", default="")
    args = parser.parse_args()

    pairs = {row["pair_id"]: row for row in read_jsonl(Path(args.pairs))}
    prefs: list[dict[str, str]] = []
    if args.judge:
        prefs.extend(load_judge_preferences(args.judge))
    if args.human_responses:
        prefs.extend(load_human_majority_preferences(args.human_responses, pairs))
    records = records_from_prefs(pairs, prefs)
    if not records:
        raise SystemExit("No valid pairwise preference records found")

    systems = sorted({row["system_a_id"] for row in records} | {row["system_b_id"] for row in records})
    observed = score_rates(records, systems)
    rng = random.Random(args.seed)
    samples: dict[str, list[float]] = {system: [] for system in systems}
    top_counts: Counter[str] = Counter()
    no_comparison_counts: Counter[str] = Counter()

    for _ in range(args.iterations):
        sample = [records[rng.randrange(len(records))] for _ in range(len(records))]
        rates = score_rates(sample, systems)
        for system, rate in rates.items():
            if rate is None:
                no_comparison_counts[system] += 1
            else:
                samples[system].append(rate)
        valid_rates = {system: rate for system, rate in rates.items() if rate is not None}
        if valid_rates:
            best = max(valid_rates.values())
            winners = sorted(system for system, rate in valid_rates.items() if rate == best)
            for system in winners:
                top_counts[system] += 1 / len(winners)

    summary: dict[str, Any] = {
        "title": args.title,
        "iterations": args.iterations,
        "seed": args.seed,
        "records": len(records),
        "systems": systems,
        "sources": dict(sorted(Counter(row["source"] for row in records).items())),
        "systems_summary": {},
    }
    for system in systems:
        vals = samples[system]
        observed_rate = observed[system]
        summary["systems_summary"][system] = {
            "observed_score_rate": observed_rate,
            "bootstrap_mean": sum(vals) / len(vals) if vals else None,
            "ci_2_5": percentile(vals, 0.025) if vals else None,
            "ci_50": percentile(vals, 0.5) if vals else None,
            "ci_97_5": percentile(vals, 0.975) if vals else None,
            "top_frequency": top_counts[system] / args.iterations,
            "no_comparison_samples": no_comparison_counts[system],
        }

    lines = [
        f"# {args.title}",
        "",
        "This report bootstraps pairwise preference rows with replacement. It quantifies small-sample uncertainty and should be treated as a diagnostic, not a calibrated benchmark confidence interval.",
        "",
        "## Coverage",
        "",
        f"- Preference records: {len(records)}",
        f"- Bootstrap iterations: {args.iterations}",
        f"- Seed: {args.seed}",
        f"- Systems: {len(systems)}",
        "",
        "## Preference Sources",
        "",
    ]
    for source, count in summary["sources"].items():
        lines.append(f"- `{source}`: {count}")
    lines.extend(
        [
            "",
            "## Score-Rate Uncertainty",
            "",
            "| System | Observed score rate | Bootstrap mean | 2.5% | 50% | 97.5% | Top frequency | No-comparison samples |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, data in sorted(summary["systems_summary"].items(), key=lambda item: (-(item[1]["observed_score_rate"] or 0.0), item[0])):
        lines.append(
            f"| {system} | {data['observed_score_rate']:.3f} | {data['bootstrap_mean']:.3f} | {data['ci_2_5']:.3f} | {data['ci_50']:.3f} | {data['ci_97_5']:.3f} | {data['top_frequency']:.3f} | {data['no_comparison_samples']} |"
        )

    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- Bootstrap samples resample preference rows, not topics or papers; topic-level uncertainty is not captured.",
            "- Systems with few comparisons can have wide intervals and occasional bootstrap samples with no comparisons.",
            "- Top frequency is the fraction of bootstrap samples where a system ties for or holds the highest score rate, split equally among ties.",
        ]
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote bootstrap uncertainty report to {output}")
    if args.json_output:
        print(f"Wrote bootstrap uncertainty JSON to {args.json_output}")


if __name__ == "__main__":
    main()
