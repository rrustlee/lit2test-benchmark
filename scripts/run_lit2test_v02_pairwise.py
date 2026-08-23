#!/usr/bin/env python3
"""Run blind pairwise judging for the Lit2Test v0.2 pilot.

This compares generator outputs within the same paper context. Model names are
hidden from the judge and A/B order is deterministic-randomized by seed.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import signal
import statistics
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = ROOT / "data" / "lit2test_v02_pilot_contexts_12.jsonl"
OUT_ROOT = ROOT / "outputs" / "lit2test_v02_pilot" / "pairwise_blind_v01"
TASKS = OUT_ROOT / "pairwise_tasks.jsonl"
TASK_REPORT_MD = ROOT / "analysis" / "lit2test_v02_pairwise_blind_task_prep.md"
TASK_REPORT_JSON = ROOT / "analysis" / "lit2test_v02_pairwise_blind_task_prep.json"
SUMMARY_MD = ROOT / "analysis" / "lit2test_v02_pairwise_blind_summary.md"
SUMMARY_JSON = ROOT / "analysis" / "lit2test_v02_pairwise_blind_summary.json"

GENERATIONS = {
    "GPT 5.2": ROOT / "outputs" / "lit2test_v02_pilot" / "generations_gpt52" / "lit2test_outputs_validated.jsonl",
    "DeepSeek-V3.2": ROOT / "outputs" / "lit2test_v02_pilot" / "generations_deepseek_v32" / "lit2test_outputs_validated.jsonl",
    "GLM-5": ROOT / "outputs" / "lit2test_v02_pilot" / "generations_glm5" / "lit2test_outputs_validated.jsonl",
}

RUBRIC_FIELDS = [
    "literature_grounding",
    "cross_paper_tension",
    "hypothesis_clarity",
    "minimal_test_adequacy",
    "metric_mechanism_match",
    "falsifiability",
    "non_genericity",
]


class RequestTimeout(RuntimeError):
    pass


def _raise_timeout(signum: int, frame: Any) -> None:  # noqa: ARG001
    raise RequestTimeout("outer request timeout")


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


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        return json.dumps(content, ensure_ascii=False)
    if isinstance(content, list):
        return "\n".join(normalize_content(item) for item in content)
    return str(content)


def extract_json_object(text: Any) -> dict[str, Any]:
    stripped = normalize_content(text).strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def mean(values: list[float]) -> float:
    return round(statistics.mean(values), 3) if values else 0.0


def safe_model_id(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model).strip("_")


def display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def compact_context(context: dict[str, Any]) -> dict[str, Any]:
    papers = []
    for paper in context.get("papers", []):
        papers.append(
            {
                "title": paper.get("title"),
                "abstract": paper.get("abstract"),
                "key_contribution": paper.get("key_contribution"),
                "limitation": paper.get("limitation"),
                "important_result": paper.get("important_result"),
            }
        )
    return {
        "context_id": context.get("context_id"),
        "field": context.get("field"),
        "research_context": context.get("research_context"),
        "open_problem": context.get("open_problem"),
        "resource_constraint": context.get("resource_constraint"),
        "papers": papers,
    }


def compact_answer(output: dict[str, Any]) -> dict[str, Any]:
    return {
        key: output.get(key)
        for key in [
            "literature_gap",
            "hypothesis",
            "minimal_test",
            "decisive_metric",
            "supporting_result",
            "falsifying_result",
        ]
    }


def load_generation_by_context(generations: dict[str, Path]) -> dict[str, dict[str, dict[str, Any]]]:
    by_context: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for system, path in generations.items():
        for row in read_jsonl(path):
            by_context[str(row["context_id"])][system] = row
    return by_context


def build_tasks(contexts_path: Path, generations: dict[str, Path], seed: int, limit_contexts: int = 0, context_ids: set[str] | None = None) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    contexts = read_jsonl(contexts_path)
    if context_ids is not None:
        contexts = [row for row in contexts if row.get("context_id") in context_ids]
    if limit_contexts:
        contexts = contexts[:limit_contexts]
    outputs = load_generation_by_context(generations)
    tasks = []
    for context in contexts:
        context_id = str(context["context_id"])
        systems = sorted(outputs[context_id])
        if set(systems) != set(generations):
            missing = sorted(set(generations) - set(systems))
            raise RuntimeError(f"Missing generations for {context_id}: {missing}")
        for system_x, system_y in combinations(sorted(generations), 2):
            left_first = rng.choice([True, False])
            if left_first:
                system_a, system_b = system_x, system_y
            else:
                system_a, system_b = system_y, system_x
            pair_slug = f"{safe_model_id(system_x)}__vs__{safe_model_id(system_y)}"
            tasks.append(
                {
                    "pair_id": f"{context_id}__{pair_slug}",
                    "context_id": context_id,
                    "base_topic_id": context.get("base_topic_id"),
                    "field": context.get("field"),
                    "system_a": system_a,
                    "system_b": system_b,
                    "canonical_system_x": system_x,
                    "canonical_system_y": system_y,
                    "answer_a": compact_answer(outputs[context_id][system_a]),
                    "answer_b": compact_answer(outputs[context_id][system_b]),
                    "context": compact_context(context),
                    "source_policy": "blind_same_context_model_pairwise_v02_no_release_no_leaderboard",
                }
            )
    return tasks


def write_task_report(tasks: list[dict[str, Any]], seed: int, out_path: Path, report_md: Path, report_json: Path, generations: dict[str, Path]) -> None:
    side_counts = Counter()
    canonical_counts = Counter()
    for row in tasks:
        side_counts[row["system_a"]] += 1
        side_counts[row["system_b"]] += 1
        canonical_counts[f"{row['canonical_system_x']} vs {row['canonical_system_y']}"] += 1
    report = {
        "status": "pass",
        "policy": "no_api_blind_same_context_pairwise_task_prep_no_release_no_leaderboard",
        "seed": seed,
        "tasks": len(tasks),
        "contexts": len({row["context_id"] for row in tasks}),
        "systems": sorted(generations),
        "system_side_exposures": dict(side_counts),
        "canonical_pair_counts": dict(canonical_counts),
        "output_file": display(out_path),
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
    }
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Lit2Test v0.2 Blind Pairwise Task Prep",
        "",
        "This prepares same-context model-output pairwise tasks. Model identities are hidden from judges; A/B order is randomized by seed.",
        "",
        f"- Status: `{report['status']}`",
        f"- Policy: `{report['policy']}`",
        f"- Seed: `{seed}`",
        f"- Tasks: `{report['tasks']}`",
        f"- Contexts: `{report['contexts']}`",
        f"- Systems: `{report['systems']}`",
        f"- System side exposures: `{report['system_side_exposures']}`",
        f"- Canonical pair counts: `{report['canonical_pair_counts']}`",
        f"- Output file: `{report['output_file']}`",
        f"- Release ready: `{report['release_ready']}`",
        f"- Allowed to publish leaderboard: `{report['allowed_to_publish_leaderboard']}`",
    ]
    report_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_prompt(task: dict[str, Any]) -> str:
    return f"""You are judging two anonymous Lit2Test answers for the same literature context.

The original task: derive one minimal falsifiable next-step test from the provided paper neighborhood. Prefer the answer that is more grounded in the provided papers, uses cross-paper tension, gives a specific hypothesis, proposes a minimal feasible test, matches metrics to mechanisms, and states clear supporting/falsifying outcomes.

Important judging rules:
- The two answers are anonymous. Do not infer or discuss model identity.
- Judge relative quality only for this specific context.
- Penalize generic research proposals that would fit many unrelated paper groups.
- Penalize large unfocused experimental programs; reward a minimal decisive test.
- If both are truly equivalent, choose "tie".

Return valid JSON only with this schema:
{{
  "pair_id": "...",
  "winner": "A" | "B" | "tie",
  "confidence": "low" | "medium" | "high",
  "main_reason": "...",
  "weakness_a": "...",
  "weakness_b": "..."
}}

Context:
```json
{json.dumps(task['context'], ensure_ascii=False, indent=2)}
```

Answer A:
```json
{json.dumps(task['answer_a'], ensure_ascii=False, indent=2)}
```

Answer B:
```json
{json.dumps(task['answer_b'], ensure_ascii=False, indent=2)}
```
"""


def call_chat(client: OpenAI, model: str, prompt: str, temperature: float, max_tokens: int, timeout: float) -> str:
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return normalize_content(response.choices[0].message.content)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def validate_judgment(judgment: dict[str, Any], pair_id: str) -> list[str]:
    errors: list[str] = []
    if str(judgment.get("winner", "")).strip() not in {"A", "B", "tie"}:
        errors.append("invalid winner")
    confidence = judgment.get("confidence")
    if isinstance(confidence, str):
        if confidence.strip().lower() not in {"low", "medium", "high"}:
            errors.append("invalid confidence")
    elif isinstance(confidence, (int, float)):
        if not 0 <= float(confidence) <= 1 and not 1 <= float(confidence) <= 5:
            errors.append("invalid confidence")
    elif confidence is not None:
        errors.append("invalid confidence")
    scores = judgment.get("scores")
    if scores is None:
        return errors
    if not isinstance(scores, dict):
        return errors + ["invalid scores"]
    for side in ["A", "B"]:
        side_scores = scores.get(side)
        if not isinstance(side_scores, dict):
            errors.append(f"missing scores.{side}")
            continue
        for field in RUBRIC_FIELDS:
            value = side_scores.get(field)
            if not isinstance(value, (int, float)) or not 1 <= float(value) <= 5:
                errors.append(f"invalid score {side}.{field}={value!r}")
    return errors


def run_judge(args: argparse.Namespace) -> None:
    if not args.api_key:
        raise SystemExit("Missing API key. Set OPENAI_API_KEY or API_KEY.")
    tasks = read_jsonl(Path(args.tasks))
    if args.limit:
        tasks = tasks[: args.limit]
    out_dir = Path(args.output_dir)
    output = out_dir / "pairwise_judgments.jsonl"
    raw_output = out_dir / "raw_pairwise_judgments.jsonl"
    completed = set()
    if output.exists() and not args.overwrite:
        completed = {row.get("pair_id") for row in read_jsonl(output) if row.get("pair_id")}
    if args.overwrite:
        output.write_text("", encoding="utf-8")
        raw_output.write_text("", encoding="utf-8")
    pending = [row for row in tasks if row["pair_id"] not in completed]
    if args.dry_run:
        print(f"DRY RUN judge={args.judge_model} pending={len(pending)} completed={len(completed)}")
        return
    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    for task in pending:
        pair_id = task["pair_id"]
        prompt = build_prompt(task)
        print(f"Pairwise judging {pair_id} with {args.judge_model}", flush=True)
        raw_text = ""
        try:
            raw_text = call_chat(client, args.judge_model, prompt, args.temperature, args.max_tokens, args.timeout)
            append_jsonl(raw_output, {"pair_id": pair_id, "judge_model": args.judge_model, "raw_text": raw_text})
            parsed = extract_json_object(raw_text)
            parsed.setdefault("pair_id", pair_id)
            errors = validate_judgment(parsed, pair_id)
            winner = str(parsed.get("winner", "")).strip()
            winning_system = None
            if winner == "A":
                winning_system = task["system_a"]
            elif winner == "B":
                winning_system = task["system_b"]
            row = {
                "pair_id": pair_id,
                "context_id": task["context_id"],
                "judge_model": args.judge_model,
                "system_a": task["system_a"],
                "system_b": task["system_b"],
                "winner": winner,
                "winning_system": winning_system,
                "confidence": parsed.get("confidence"),
                "scores": parsed.get("scores"),
                "main_reason": parsed.get("main_reason"),
                "weakness_a": parsed.get("weakness_a"),
                "weakness_b": parsed.get("weakness_b"),
                "judge_errors": errors,
            }
        except Exception as exc:  # noqa: BLE001
            row = {
                "pair_id": pair_id,
                "context_id": task["context_id"],
                "judge_model": args.judge_model,
                "system_a": task["system_a"],
                "system_b": task["system_b"],
                "winner": None,
                "winning_system": None,
                "confidence": None,
                "scores": None,
                "main_reason": None,
                "weakness_a": None,
                "weakness_b": None,
                "judge_errors": [f"{type(exc).__name__}: {exc}"],
                "raw_text": raw_text,
            }
        append_jsonl(output, row)
        if args.sleep:
            time.sleep(args.sleep)
    print(f"Wrote pairwise judgments to {output}")


def fatal_judge_errors(row: dict[str, Any]) -> list[str]:
    """Return errors that make the pairwise winner unusable.

    Some judges reliably choose A/B but rewrite pair_id or use a different
    confidence/rubric scale. Those are schema-quality issues, not fatal for the
    blind pairwise win/loss diagnostic.
    """

    winner = row.get("winner")
    fatal = []
    if winner not in {"A", "B", "tie"}:
        fatal.append("missing_or_invalid_winner")
    if winner in {"A", "B"} and not row.get("winning_system"):
        fatal.append("missing_winning_system")
    return fatal


def side_score(row: dict[str, Any], side: str) -> float | None:
    scores = row.get("scores")
    if not isinstance(scores, dict) or not isinstance(scores.get(side), dict):
        return None
    vals = [scores[side].get(field) for field in RUBRIC_FIELDS]
    if not all(isinstance(value, (int, float)) and 1 <= float(value) <= 5 for value in vals):
        return None
    return float(sum(vals) / len(vals))


def confidence_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        mapping = {"low": 1.0, "medium": 2.0, "high": 3.0}
        return mapping.get(value.strip().lower(), 0.0)
    return 0.0


def summarize(paths: list[Path], tasks_path: Path, systems: list[str]) -> dict[str, Any]:
    tasks = {row["pair_id"]: row for row in read_jsonl(tasks_path)}
    rows: list[dict[str, Any]] = []
    for path in paths:
        if path.exists():
            rows.extend(read_jsonl(path))
    valid = [row for row in rows if not fatal_judge_errors(row)]
    schema_issue_rows = [row for row in rows if row.get("judge_errors") and not fatal_judge_errors(row)]
    win_counts = Counter(row.get("winning_system") for row in valid if row.get("winning_system"))
    tie_count = sum(1 for row in valid if row.get("winner") == "tie")
    exposure = Counter()
    side_wins = Counter()
    by_system_scores: dict[str, list[float]] = defaultdict(list)
    by_context: dict[str, Counter[str]] = defaultdict(Counter)
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in valid:
        task = tasks.get(row["pair_id"], {})
        for side, system in [("A", row.get("system_a")), ("B", row.get("system_b"))]:
            if system:
                exposure[f"{system}_as_{side}"] += 1
                score = side_score(row, side)
                if score is not None:
                    by_system_scores[str(system)].append(score)
        if row.get("winner") in {"A", "B"}:
            side_wins[str(row.get("winner"))] += 1
        if row.get("winning_system"):
            by_context[str(row.get("context_id"))][str(row.get("winning_system"))] += 1
        elif row.get("winner") == "tie":
            by_context[str(row.get("context_id"))]["tie"] += 1
        canonical = " vs ".join([str(task.get("canonical_system_x")), str(task.get("canonical_system_y"))])
        by_pair[canonical].append(row)

    pair_records = {}
    for canonical, prows in sorted(by_pair.items()):
        counter = Counter(row.get("winning_system") or "tie" for row in prows)
        pair_records[canonical] = {
            "rows": len(prows),
            "wins": dict(counter),
            "mean_confidence": mean([confidence_value(row.get("confidence")) for row in prows]),
        }

    agreement_cases = []
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for row in valid:
        grouped[row["pair_id"]][row["judge_model"]] = row.get("winning_system") or "tie"
    for pair_id, judge_votes in sorted(grouped.items()):
        if len(judge_votes) < 2:
            continue
        votes = list(judge_votes.values())
        agreement_cases.append({"pair_id": pair_id, "votes": judge_votes, "agree": len(set(votes)) == 1})
    agreement_total = len(agreement_cases)
    agreement_count = sum(1 for row in agreement_cases if row["agree"])

    report = {
        "status": "pass" if rows and len(rows) == len(valid) else "partial",
        "policy": "blind_same_context_pairwise_diagnostic_no_release_no_leaderboard",
        "task_file": display(tasks_path),
        "judgment_files": [display(path) for path in paths],
        "rows": len(rows),
        "valid_rows": len(valid),
        "fatal_judge_errors": len(rows) - len(valid),
        "schema_issue_rows": len(schema_issue_rows),
        "tasks": len(tasks),
        "judges": sorted({row.get("judge_model") for row in rows}),
        "systems": sorted(systems),
        "system_wins": dict(win_counts),
        "ties": tie_count,
        "system_mean_pairwise_scores": {system: mean(vals) for system, vals in sorted(by_system_scores.items())},
        "side_exposure": dict(exposure),
        "side_wins": dict(side_wins),
        "canonical_pair_records": pair_records,
        "context_win_counts": {context_id: dict(counter) for context_id, counter in sorted(by_context.items())},
        "judge_agreement": {
            "comparable_pairs": agreement_total,
            "agreements": agreement_count,
            "agreement_rate": round(agreement_count / agreement_total, 3) if agreement_total else 0.0,
        },
        "agreement_cases": agreement_cases,
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
    }
    return report


def write_summary(report: dict[str, Any], summary_md: Path, summary_json: Path) -> None:
    summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Lit2Test v0.2 Blind Pairwise Summary",
        "",
        "This is a blind same-context pairwise diagnostic. It is not a release benchmark and not a leaderboard.",
        "",
        f"- Status: `{report['status']}`",
        f"- Policy: `{report['policy']}`",
        f"- Rows: `{report['rows']}`",
        f"- Valid rows: `{report['valid_rows']}`",
        f"- Fatal judge errors: `{report['fatal_judge_errors']}`",
        f"- Schema issue rows: `{report['schema_issue_rows']}`",
        f"- Tasks: `{report['tasks']}`",
        f"- Judges: `{report['judges']}`",
        f"- Release ready: `{report['release_ready']}`",
        f"- Allowed to publish leaderboard: `{report['allowed_to_publish_leaderboard']}`",
        "",
        "## System Wins",
        "",
        "| System | Wins | Optional mean side score |",
        "|---|---:|---:|",
    ]
    for system in report["systems"]:
        lines.append(
            f"| `{system}` | {report['system_wins'].get(system, 0)} | "
            f"{report['system_mean_pairwise_scores'].get(system, 0)} |"
        )
    lines.extend([
        f"| `tie` | {report['ties']} |  |",
        "",
        "## Canonical Pair Records",
        "",
        "| Pair | Rows | Wins | Mean confidence |",
        "|---|---:|---|---:|",
    ])
    for pair, item in report["canonical_pair_records"].items():
        lines.append(f"| `{pair}` | {item['rows']} | `{item['wins']}` | {item['mean_confidence']} |")
    agreement = report["judge_agreement"]
    lines.extend([
        "",
        "## Judge Agreement",
        "",
        f"- Comparable pairs: `{agreement['comparable_pairs']}`",
        f"- Agreements: `{agreement['agreements']}`",
        f"- Agreement rate: `{agreement['agreement_rate']}`",
        "",
        "## Side Check",
        "",
        f"- Side exposure: `{report['side_exposure']}`",
        f"- Side wins: `{report['side_wins']}`",
        "",
        "## Interpretation",
        "",
        "Use this to diagnose whether the rubric-score ordering survives blind relative comparison. Do not publish it as a final model ranking without broader item coverage and judge calibration.",
    ])
    summary_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_generation_args(values: list[str] | None) -> dict[str, Path]:
    if not values:
        return GENERATIONS
    if len(values) % 2 != 0:
        raise SystemExit("--generation must be repeated as SYSTEM PATH pairs")
    return {values[i]: Path(values[i + 1]) for i in range(0, len(values), 2)}


def read_context_id_file(path: str | None) -> set[str] | None:
    if not path:
        return None
    ids = set()
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ids.add(line)
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Lit2Test v0.2 blind pairwise diagnostics")
    subparsers = parser.add_subparsers(required=True)

    p = subparsers.add_parser("prepare")
    p.add_argument("--contexts", default=str(CONTEXTS))
    p.add_argument("--tasks", default=str(TASKS))
    p.add_argument("--report", default=str(TASK_REPORT_MD))
    p.add_argument("--json-report", default=str(TASK_REPORT_JSON))
    p.add_argument("--generation", nargs="*", default=None, help="SYSTEM PATH pairs overriding default pilot generations")
    p.add_argument("--context-id-file", default=None)
    p.add_argument("--seed", type=int, default=20260620)
    p.add_argument("--limit-contexts", type=int, default=0)
    p.set_defaults(mode="prepare")

    p = subparsers.add_parser("judge")
    p.add_argument("--tasks", default=str(TASKS))
    p.add_argument("--output-dir", required=True)
    p.add_argument("--judge-model", default="GPT 5.2")
    p.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "${API_BASE_URL}"))
    p.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY"))
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--max-tokens", type=int, default=1200)
    p.add_argument("--timeout", type=float, default=90.0)
    p.add_argument("--sleep", type=float, default=0.2)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(mode="judge")

    p = subparsers.add_parser("summarize")
    p.add_argument("--tasks", default=str(TASKS))
    p.add_argument("--judgments", nargs="+", required=True)
    p.add_argument("--systems", nargs="+", default=sorted(GENERATIONS))
    p.add_argument("--report", default=str(SUMMARY_MD))
    p.add_argument("--json-report", default=str(SUMMARY_JSON))
    p.set_defaults(mode="summarize")

    args = parser.parse_args()
    if args.mode == "prepare":
        generations = parse_generation_args(args.generation)
        context_ids = read_context_id_file(args.context_id_file)
        tasks_path = Path(args.tasks)
        tasks = build_tasks(Path(args.contexts), generations, seed=args.seed, limit_contexts=args.limit_contexts, context_ids=context_ids)
        write_jsonl(tasks_path, tasks)
        write_task_report(tasks, args.seed, tasks_path, Path(args.report), Path(args.json_report), generations)
        print(f"Prepared {len(tasks)} blind pairwise tasks at {tasks_path}")
    elif args.mode == "judge":
        run_judge(args)
    elif args.mode == "summarize":
        report = summarize([Path(path) for path in args.judgments], Path(args.tasks), args.systems)
        write_summary(report, Path(args.report), Path(args.json_report))
        print(f"Pairwise summary status: {report['status']} rows={report['rows']} valid={report['valid_rows']}")


if __name__ == "__main__":
    main()
