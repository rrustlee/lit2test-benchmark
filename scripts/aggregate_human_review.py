#!/usr/bin/env python3
"""Aggregate anonymized human pairwise review responses."""

from __future__ import annotations

import argparse
import csv
import json
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


def write_template(path: Path, pairs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["reviewer_id", "pair_id", "choice", "confidence", "notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pair in pairs:
            writer.writerow({"reviewer_id": "", "pair_id": pair["pair_id"], "choice": "", "confidence": "", "notes": ""})


def load_pairwise_judge(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    winners: dict[str, str] = {}
    for row in read_jsonl(path):
        judgment = row.get("judgment")
        winner = str(judgment.get("winner", "")).strip() if judgment else ""
        if winner in VALID_CHOICES:
            winners[row["pair_id"]] = winner
    return winners


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Lit2Test human pairwise responses")
    parser.add_argument("--pairs", default=str(ROOT / "outputs" / "claim_audited_balanced_pairs_smoke.jsonl"))
    parser.add_argument("--responses", default=str(ROOT / "outputs" / "human_review_claim_audited" / "responses_template.csv"))
    parser.add_argument("--template", action="store_true", help="Write a blank response CSV template and exit")
    parser.add_argument("--judge-a", default=str(ROOT / "outputs" / "claim_audited_pairwise_judgments_gpt52_smoke.jsonl"))
    parser.add_argument("--judge-b", default=str(ROOT / "outputs" / "claim_audited_pairwise_judgments_deepseekv32_smoke.jsonl"))
    parser.add_argument("--judge-a-name", default="GPT 5.2")
    parser.add_argument("--judge-b-name", default="DeepSeek-V3.2")
    parser.add_argument("--output", default=str(ROOT / "analysis" / "human_review_claim_audited_report.md"))
    parser.add_argument("--disclaimer", default="", help="Optional note inserted near the top of the report")
    args = parser.parse_args()

    pairs = read_jsonl(Path(args.pairs))
    pair_meta = {pair["pair_id"]: pair for pair in pairs}

    if args.template:
        write_template(Path(args.responses), pairs)
        print(f"Wrote blank human response template to {args.responses}")
        return

    responses_path = Path(args.responses)
    if not responses_path.exists():
        raise SystemExit(f"Missing responses CSV: {responses_path}. Run with --template first.")

    responses = read_csv(responses_path)
    usable = []
    invalid = []
    for row in responses:
        pair_id = row.get("pair_id", "").strip()
        choice = row.get("choice", "").strip()
        if not choice:
            continue
        if pair_id not in pair_meta or choice not in VALID_CHOICES:
            invalid.append(row)
            continue
        usable.append(row)

    votes_by_pair: dict[str, Counter[str]] = defaultdict(Counter)
    confidence_counts: Counter[str] = Counter()
    reviewers = set()
    for row in usable:
        pair_id = row["pair_id"].strip()
        choice = row["choice"].strip()
        reviewer = row.get("reviewer_id", "").strip() or "anonymous"
        confidence = row.get("confidence", "").strip() or "unspecified"
        reviewers.add(reviewer)
        votes_by_pair[pair_id][choice] += 1
        confidence_counts[confidence] += 1

    majority_by_pair: dict[str, str] = {}
    unresolved = 0
    for pair_id, counts in votes_by_pair.items():
        if not counts:
            continue
        top = counts.most_common()
        if len(top) > 1 and top[0][1] == top[1][1]:
            majority_by_pair[pair_id] = "tie"
            unresolved += 1
        else:
            majority_by_pair[pair_id] = top[0][0]

    wins: dict[str, Counter[str]] = defaultdict(Counter)
    topic_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for pair_id, choice in majority_by_pair.items():
        pair = pair_meta[pair_id]
        topic_counts[pair["topic_id"]][choice] += 1
        for system_id in (pair["system_a_id"], pair["system_b_id"]):
            wins[system_id]["comparisons"] += 1
        if choice == "A":
            wins[pair["system_a_id"]]["wins"] += 1
            wins[pair["system_b_id"]]["losses"] += 1
        elif choice == "B":
            wins[pair["system_b_id"]]["wins"] += 1
            wins[pair["system_a_id"]]["losses"] += 1
        else:
            wins[pair["system_a_id"]]["ties"] += 1
            wins[pair["system_b_id"]]["ties"] += 1

    judge_a = load_pairwise_judge(Path(args.judge_a))
    judge_b = load_pairwise_judge(Path(args.judge_b))
    judge_agree = {args.judge_a_name: 0, args.judge_b_name: 0}
    judge_total = {args.judge_a_name: 0, args.judge_b_name: 0}
    for pair_id, choice in majority_by_pair.items():
        for name, judgments in ((args.judge_a_name, judge_a), (args.judge_b_name, judge_b)):
            if pair_id in judgments:
                judge_total[name] += 1
                if judgments[pair_id] == choice:
                    judge_agree[name] += 1

    lines = [
        "# Lit2Test Human Review Aggregation",
        "",
        "This report aggregates anonymized human pairwise responses. It is empty or partial until reviewers fill the response CSV.",
        "",
    ]
    if args.disclaimer:
        lines.extend([f"**Note:** {args.disclaimer}", ""])
    lines.extend([
        "## Coverage",
        "",
        f"- Pair tasks: {len(pairs)}",
        f"- Usable response rows: {len(usable)}",
        f"- Invalid response rows: {len(invalid)}",
        f"- Reviewers: {len(reviewers)}",
        f"- Pairs with at least one vote: {len(votes_by_pair)}",
        f"- Pairs missing votes: {len(set(pair_meta) - set(votes_by_pair))}",
        f"- Majority ties due to split votes: {unresolved}",
        "",
    ])

    if confidence_counts:
        lines.extend(["## Confidence Distribution", ""])
        for confidence, count in sorted(confidence_counts.items()):
            lines.append(f"- {confidence}: {count}")
        lines.append("")

    lines.extend([
        "## Human Majority By System",
        "",
        "| System | Comparisons | Wins | Losses | Ties | Win rate excl. ties |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for system_id in sorted(wins):
        record = wins[system_id]
        decisive = record["wins"] + record["losses"]
        win_rate = record["wins"] / decisive if decisive else 0.0
        lines.append(
            f"| {system_id} | {record['comparisons']} | {record['wins']} | {record['losses']} | {record['ties']} | {win_rate:.3f} |"
        )

    lines.extend(["", "## Human Majority By Topic", "", "| Topic | A | B | tie |", "|---|---:|---:|---:|"])
    for topic_id in sorted({pair["topic_id"] for pair in pairs}):
        counts = topic_counts[topic_id]
        lines.append(f"| {topic_id} | {counts['A']} | {counts['B']} | {counts['tie']} |")

    lines.extend(["", "## LLM Judge Agreement With Human Majority", ""])
    for name in [args.judge_a_name, args.judge_b_name]:
        total = judge_total[name]
        if total:
            lines.append(f"- {name}: {judge_agree[name]}/{total} = {judge_agree[name] / total:.3f}")
        else:
            lines.append(f"- {name}: no overlapping human-majority pairs")

    missing_pairs = sorted(set(pair_meta) - set(votes_by_pair))
    lines.extend(["", "## Missing Or Invalid Responses", ""])
    if missing_pairs:
        lines.append("Missing pair IDs:")
        lines.append("")
        for pair_id in missing_pairs:
            lines.append(f"- `{pair_id}`")
    else:
        lines.append("No missing pair IDs.")
    if invalid:
        lines.extend(["", "Invalid rows:", "", "| reviewer_id | pair_id | choice |", "|---|---|---|"])
        for row in invalid:
            lines.append(f"| {row.get('reviewer_id', '')} | {row.get('pair_id', '')} | {row.get('choice', '')} |")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote human review aggregation report to {output}")


if __name__ == "__main__":
    main()
