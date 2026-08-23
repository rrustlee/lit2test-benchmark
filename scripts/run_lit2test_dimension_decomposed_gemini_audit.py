#!/usr/bin/env python3
"""Run the frozen dimension-decomposed Gemini audit with strict validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs/lit2test_dimension_decomposed_gemini_audit"
EXPECTED_ENDPOINT = os.environ.get("JUDGE_BASE_URL", "${API_BASE_URL}") + "/responses"
DIMENSIONS = (
    "grounding",
    "hypothesis_specificity",
    "minimality_feasibility",
    "decisive_metric",
    "falsifiability",
)
TOP_LEVEL_FIELDS = {
    "audit_id",
    "pair_id",
    "order",
    "dimensions",
    "overall_winner",
    "overall_confidence",
    "overall_reason",
}
DIMENSION_FIELDS = {"score_a", "score_b", "winner", "reason"}
WINNERS = {"A", "B", "tie"}
CONFIDENCES = {"low", "medium", "high"}
PARTICIPANT_MODELS = {
    "GPT 5.2",
    "Claude-Sonnet-4.6",
    "GLM-5",
    "DeepSeek-V3.2",
}


def now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_no}")
            rows.append(value)
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(normalize_content(item) for item in value)
    if isinstance(value, dict):
        if "text" in value:
            return normalize_content(value["text"])
        if "content" in value:
            return normalize_content(value["content"])
        return ""
    return str(value)


def extract_response_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if isinstance(candidates, list) and candidates:
        candidate = candidates[0]
        if isinstance(candidate, dict):
            content = candidate.get("content", {})
            if isinstance(content, dict):
                text = normalize_content(content.get("parts"))
                if text.strip():
                    return text
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    output = payload.get("output")
    if isinstance(output, list):
        text = normalize_content(output)
        if text.strip():
            return text
    raise ValueError("response payload contains no supported model text")


def parse_model_json(text: str) -> tuple[dict[str, Any], str | None]:
    stripped = text.strip()
    normalization: str | None = None
    if stripped.startswith("```") and stripped.endswith("```"):
        first_newline = stripped.find("\n")
        if first_newline < 0:
            raise json.JSONDecodeError("empty Markdown code fence", stripped, 0)
        opening = stripped[:first_newline].strip().lower()
        if opening not in {"```", "```json"}:
            raise json.JSONDecodeError("unsupported Markdown code fence", stripped, 0)
        stripped = stripped[first_newline + 1 : -3].strip()
        normalization = "single_outer_markdown_json_fence_removed"
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("model JSON is not an object")
    return parsed, normalization


def score_winner(score_a: int, score_b: int) -> str:
    if score_a > score_b:
        return "A"
    if score_b > score_a:
        return "B"
    return "tie"


def validate_parsed(parsed: Any, task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(parsed, dict):
        return ["top_level_not_object"]
    if set(parsed) != TOP_LEVEL_FIELDS:
        missing = sorted(TOP_LEVEL_FIELDS - set(parsed))
        extra = sorted(set(parsed) - TOP_LEVEL_FIELDS)
        errors.append(f"top_level_fields:missing={missing}:extra={extra}")
    for field in ("audit_id", "pair_id", "order"):
        if parsed.get(field) != task.get(field):
            errors.append(f"{field}_mismatch:{parsed.get(field)!r}!={task.get(field)!r}")
    if parsed.get("order") not in {"original", "reverse"}:
        errors.append("invalid_order")

    dimensions = parsed.get("dimensions")
    if not isinstance(dimensions, dict):
        errors.append("dimensions_not_object")
    else:
        if set(dimensions) != set(DIMENSIONS):
            errors.append(
                f"dimension_keys:missing={sorted(set(DIMENSIONS) - set(dimensions))}:"
                f"extra={sorted(set(dimensions) - set(DIMENSIONS))}"
            )
        for name in DIMENSIONS:
            item = dimensions.get(name)
            if not isinstance(item, dict):
                errors.append(f"{name}_not_object")
                continue
            if set(item) != DIMENSION_FIELDS:
                errors.append(
                    f"{name}_fields:missing={sorted(DIMENSION_FIELDS - set(item))}:"
                    f"extra={sorted(set(item) - DIMENSION_FIELDS)}"
                )
            score_a = item.get("score_a")
            score_b = item.get("score_b")
            if type(score_a) is not int or score_a not in {1, 2, 3}:  # bool is not a score
                errors.append(f"{name}.invalid_score_a:{score_a!r}")
            if type(score_b) is not int or score_b not in {1, 2, 3}:
                errors.append(f"{name}.invalid_score_b:{score_b!r}")
            winner = item.get("winner")
            if winner not in WINNERS:
                errors.append(f"{name}.invalid_winner:{winner!r}")
            if type(score_a) is int and type(score_b) is int and score_a in {1, 2, 3} and score_b in {1, 2, 3}:
                expected = score_winner(score_a, score_b)
                if winner != expected:
                    errors.append(f"{name}.winner_score_mismatch:{winner!r}!={expected!r}")
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                errors.append(f"{name}.empty_reason")

    if parsed.get("overall_winner") not in WINNERS:
        errors.append(f"invalid_overall_winner:{parsed.get('overall_winner')!r}")
    if parsed.get("overall_confidence") not in CONFIDENCES:
        errors.append(f"invalid_overall_confidence:{parsed.get('overall_confidence')!r}")
    if not isinstance(parsed.get("overall_reason"), str) or not parsed["overall_reason"].strip():
        errors.append("empty_overall_reason")

    reason_texts: list[str] = []
    if isinstance(dimensions, dict):
        reason_texts.extend(
            item.get("reason", "") for item in dimensions.values() if isinstance(item, dict)
        )
    reason_texts.append(parsed.get("overall_reason", ""))
    joined_reasons = "\n".join(str(value) for value in reason_texts).casefold()
    for system in PARTICIPANT_MODELS:
        if system.casefold() in joined_reasons:
            errors.append(f"model_identity_mentioned:{system}")
    return errors


def render_prompt(template: str, task: dict[str, Any]) -> str:
    substitutions = {
        "__AUDIT_ID__": task["audit_id"],
        "__PAIR_ID__": task["pair_id"],
        "__ORDER__": task["order"],
        "__CONTEXT_JSON__": json.dumps(task["context"], ensure_ascii=False, indent=2),
        "__ANSWER_A_JSON__": json.dumps(task["answer_a"], ensure_ascii=False, indent=2),
        "__ANSWER_B_JSON__": json.dumps(task["answer_b"], ensure_ascii=False, indent=2),
    }
    prompt = template
    for placeholder, value in substitutions.items():
        if prompt.count(placeholder) != 1:
            raise ValueError(f"Prompt placeholder {placeholder} must occur exactly once")
        prompt = prompt.replace(placeholder, value)
    leftovers = [placeholder for placeholder in substitutions if placeholder in prompt]
    if leftovers:
        raise ValueError(f"Unresolved prompt placeholders: {leftovers}")
    for system in PARTICIPANT_MODELS:
        if system.casefold() in prompt.casefold():
            raise ValueError(
                f"{task['audit_id']}: rendered prompt leaks hidden model identity {system!r}; "
                "use an opaque pair_id and keep source IDs only as local metadata"
            )
    return prompt


def mechanical_fields(parsed: dict[str, Any]) -> dict[str, Any]:
    total_a = sum(parsed["dimensions"][name]["score_a"] for name in DIMENSIONS)
    total_b = sum(parsed["dimensions"][name]["score_b"] for name in DIMENSIONS)
    votes = Counter(parsed["dimensions"][name]["winner"] for name in DIMENSIONS)
    majority = score_winner(votes["A"], votes["B"])
    return {
        "score_sum_a": total_a,
        "score_sum_b": total_b,
        "score_sum_winner": score_winner(total_a, total_b),
        "dimension_votes_a": votes["A"],
        "dimension_votes_b": votes["B"],
        "dimension_votes_tie": votes["tie"],
        "dimension_majority_winner": majority,
    }


def latest_valid_ids(path: Path, tasks: dict[str, dict[str, Any]]) -> tuple[set[str], Counter[str]]:
    counts: Counter[str] = Counter()
    for row in read_jsonl(path):
        audit_id = row.get("audit_id")
        if audit_id not in tasks:
            raise ValueError(f"Parsed judgment references unknown audit_id: {audit_id!r}")
        errors = validate_parsed(row.get("judgment"), tasks[audit_id])
        if errors:
            raise ValueError(f"Stored parsed judgment {audit_id} is invalid: {errors}")
        counts[audit_id] += 1
    return set(counts), counts


def write_completion_report(
    *,
    path: Path,
    mode: str,
    all_tasks: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    judgment_path: Path,
    attempt_counts: Counter[str],
    failure_counts: Counter[str],
    duplicate_valid: dict[str, int],
) -> None:
    task_map = {row["audit_id"]: row for row in all_tasks}
    completed, stored_counts = latest_valid_ids(judgment_path, task_map)
    selected_ids = {row["audit_id"] for row in selected}
    real_ids = {row["audit_id"] for row in all_tasks if row["source_type"] == "real_model_pair"}
    control_ids = set(task_map) - real_ids
    report = {
        "updated_at": now_iso(),
        "mode": mode,
        "status": "complete" if selected_ids <= completed else "incomplete",
        "selected": len(selected_ids),
        "selected_valid": len(selected_ids & completed),
        "selected_missing": sorted(selected_ids - completed),
        "all_tasks": len(all_tasks),
        "all_valid": len(completed),
        "all_missing": sorted(set(task_map) - completed),
        "real_valid": len(real_ids & completed),
        "real_expected": len(real_ids),
        "control_valid": len(control_ids & completed),
        "control_expected": len(control_ids),
        "attempts_this_invocation": sum(attempt_counts.values()),
        "attempts_by_audit_id_this_invocation": dict(sorted(attempt_counts.items())),
        "failure_reasons_this_invocation": dict(sorted(failure_counts.items())),
        "stored_valid_records": sum(stored_counts.values()),
        "duplicate_valid_records": duplicate_valid,
        "completion_gate_188": len(all_tasks) == 188 and len(completed) == 188,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--max-attempts", type=int)
    parser.add_argument("--sleep", type=float)
    parser.add_argument("--backoff-base", type=float, default=2.0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    tasks_path = output_dir / "audit_tasks.jsonl"
    prompt_path = output_dir / "prompt.txt"
    protocol_path = output_dir / "protocol.json"
    input_audit_path = output_dir / "input_audit.json"
    for required in (tasks_path, prompt_path, protocol_path, input_audit_path):
        if not required.is_file():
            raise SystemExit(f"Missing frozen input: {required}")

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    input_audit = json.loads(input_audit_path.read_text(encoding="utf-8"))
    if input_audit.get("status") != "pass":
        raise SystemExit("Input audit is not pass")
    if sha256_file(prompt_path) != protocol.get("prompt_sha256"):
        raise SystemExit("Frozen prompt SHA-256 mismatch")
    if sha256_file(tasks_path) != protocol.get("audit_tasks_sha256"):
        raise SystemExit("Frozen audit task SHA-256 mismatch")
    endpoint = protocol.get("endpoint")
    if endpoint != EXPECTED_ENDPOINT:
        raise SystemExit(f"Unexpected endpoint in protocol: {endpoint!r}")
    model = protocol.get("model")
    if not isinstance(model, str) or not model:
        raise SystemExit("Missing model in protocol")

    tasks = read_jsonl(tasks_path)
    task_map = {row.get("audit_id"): row for row in tasks}
    if len(tasks) != 188 or len(task_map) != 188 or None in task_map:
        raise SystemExit(f"Expected 188 unique audit tasks, found rows={len(tasks)} ids={len(task_map)}")
    prompt_template = prompt_path.read_text(encoding="utf-8")
    rendered_prompts = {task["audit_id"]: render_prompt(prompt_template, task) for task in tasks}
    rendered_prompt_set_sha256 = hashlib.sha256(
        "\n\n===== NEXT AUDIT PROMPT =====\n\n".join(
            rendered_prompts[task["audit_id"]] for task in tasks
        ).encode("utf-8")
    ).hexdigest()
    if rendered_prompt_set_sha256 != protocol.get("rendered_prompt_set_sha256"):
        raise SystemExit("Frozen rendered prompt-set SHA-256 mismatch")

    smoke_ids = protocol.get("smoke_audit_ids")
    if not isinstance(smoke_ids, list) or len(smoke_ids) != 4 or len(set(smoke_ids)) != 4:
        raise SystemExit("Protocol must define four unique smoke_audit_ids")
    unknown_smoke = sorted(set(smoke_ids) - set(task_map))
    if unknown_smoke:
        raise SystemExit(f"Unknown smoke audit IDs: {unknown_smoke}")
    if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
        raise SystemExit("Invalid shard settings")
    if args.mode == "smoke" and (args.shard_count != 1 or args.shard_index != 0):
        raise SystemExit("Smoke mode does not support sharding")
    selected = [task_map[audit_id] for audit_id in smoke_ids] if args.mode == "smoke" else tasks
    if args.mode == "full" and args.shard_count > 1:
        selected = [
            task
            for task_index, task in enumerate(selected)
            if task_index % args.shard_count == args.shard_index
        ]

    judgments_path = output_dir / "judgments.jsonl"
    raw_path = output_dir / "raw_judgments.jsonl"
    log_path = output_dir / "run_log.jsonl"
    completion_path = output_dir / "completion_report.json"
    completed, stored_counts = latest_valid_ids(judgments_path, task_map)
    duplicate_valid = {key: count for key, count in sorted(stored_counts.items()) if count > 1}
    pending = [task for task in selected if task["audit_id"] not in completed]

    policy = protocol.get("request_policy", {})
    timeout = args.timeout if args.timeout is not None else float(policy.get("timeout_seconds", 180))
    max_attempts = args.max_attempts if args.max_attempts is not None else int(policy.get("max_attempts", 4))
    inter_sleep = args.sleep if args.sleep is not None else float(policy.get("inter_request_sleep_seconds", 0.5))
    if timeout <= 0 or max_attempts < 1 or inter_sleep < 0 or args.backoff_base <= 0:
        raise SystemExit("Invalid timeout/retry/sleep settings")
    print(
        f"mode={args.mode} selected={len(selected)} completed={len(selected) - len(pending)} "
        f"pending={len(pending)} workers=1 shard={args.shard_index}/{args.shard_count} model={model}",
        flush=True,
    )

    attempt_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    if args.dry_run:
        write_completion_report(
            path=completion_path,
            mode=args.mode,
            all_tasks=tasks,
            selected=selected,
            judgment_path=judgments_path,
            attempt_counts=attempt_counts,
            failure_counts=failure_counts,
            duplicate_valid=duplicate_valid,
        )
        print("DRY RUN: no API requests sent", flush=True)
        return

    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise SystemExit("Missing API_KEY environment variable")
    session = requests.Session()
    rng = random.Random(int(protocol.get("random_seed", 20260721)))

    interrupted = False
    try:
        for task_index, task in enumerate(pending):
            audit_id = task["audit_id"]
            prompt = rendered_prompts[audit_id]
            succeeded = False
            for attempt in range(1, max_attempts + 1):
                attempt_counts[audit_id] += 1
                started = time.monotonic()
                timestamp = now_iso()
                http_status: int | None = None
                response_body = ""
                response_payload: dict[str, Any] | None = None
                raw_text = ""
                error_type: str | None = None
                error_message: str | None = None
                validation_errors: list[str] = []
                format_normalization: str | None = None
                retry_after: float | None = None
                valid_row: dict[str, Any] | None = None
                try:
                    response = session.post(
                        endpoint,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={
                            "model": model,
                            "stream": False,
                            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        },
                        timeout=timeout,
                    )
                    http_status = response.status_code
                    response_body = response.text
                    if response.headers.get("Retry-After"):
                        try:
                            retry_after = float(response.headers["Retry-After"])
                        except ValueError:
                            retry_after = None
                    try:
                        decoded = response.json()
                        if isinstance(decoded, dict):
                            response_payload = decoded
                    except ValueError:
                        response_payload = None
                    if http_status >= 400:
                        error_type = f"http_{http_status}"
                        error_message = response_body[:1000]
                    elif response_payload is None:
                        error_type = "invalid_response_json"
                        error_message = "HTTP response body is not a JSON object"
                    else:
                        raw_text = extract_response_text(response_payload)
                        parsed, format_normalization = parse_model_json(raw_text)
                        validation_errors = validate_parsed(parsed, task)
                        if validation_errors:
                            error_type = "schema_validation_error"
                            error_message = "; ".join(validation_errors)
                        else:
                            valid_row = {
                                "audit_id": audit_id,
                                "case_id": task["case_id"],
                                "pair_id": task["pair_id"],
                                "source_pair_id": task.get("source_pair_id", task["pair_id"]),
                                "order": task["order"],
                                "source_type": task["source_type"],
                                "judge_model": model,
                                "attempt": attempt,
                                "validated_at": now_iso(),
                                "format_normalization": format_normalization,
                                "judgment": parsed,
                                **mechanical_fields(parsed),
                            }
                            succeeded = True
                except json.JSONDecodeError as exc:
                    error_type = "model_output_json_error"
                    error_message = str(exc)
                except (requests.RequestException, ValueError) as exc:
                    error_type = type(exc).__name__
                    error_message = str(exc)
                except Exception as exc:  # preserve unexpected failures before terminating this task
                    error_type = type(exc).__name__
                    error_message = str(exc)

                elapsed = round(time.monotonic() - started, 3)
                append_jsonl(
                    raw_path,
                    {
                        "timestamp": timestamp,
                        "audit_id": audit_id,
                        "attempt": attempt,
                        "judge_model": model,
                        "http_status": http_status,
                        "elapsed_seconds": elapsed,
                        "response_body": response_body,
                        "model_output_text": raw_text,
                        "error_type": error_type,
                        "error_message": error_message,
                        "validation_errors": validation_errors,
                        "format_normalization": format_normalization,
                    },
                )
                if valid_row is not None:
                    append_jsonl(judgments_path, valid_row)
                status = "valid" if succeeded else "failed"
                append_jsonl(
                    log_path,
                    {
                        "timestamp": timestamp,
                        "audit_id": audit_id,
                        "mode": args.mode,
                        "attempt": attempt,
                        "status": status,
                        "http_status": http_status,
                        "elapsed_seconds": elapsed,
                        "error_type": error_type,
                        "format_normalization": format_normalization,
                        "retry_scheduled": not succeeded and attempt < max_attempts,
                    },
                )
                if succeeded:
                    print(f"VALID {audit_id} attempt={attempt} elapsed={elapsed}s", flush=True)
                    break

                failure_counts[error_type or "unknown_error"] += 1
                print(
                    f"FAILED {audit_id} attempt={attempt}/{max_attempts} type={error_type} "
                    f"elapsed={elapsed}s",
                    flush=True,
                )
                if attempt < max_attempts:
                    backoff = max(retry_after or 0.0, args.backoff_base * (2 ** (attempt - 1)))
                    backoff += rng.uniform(0.0, min(1.0, backoff * 0.1))
                    time.sleep(backoff)
            if not succeeded:
                print(f"EXHAUSTED {audit_id}; rerun the same command to resume", flush=True)
            if inter_sleep and task_index + 1 < len(pending):
                time.sleep(inter_sleep)
    except KeyboardInterrupt:
        interrupted = True
        print("Interrupted; writing completion snapshot", flush=True)
    finally:
        write_completion_report(
            path=completion_path,
            mode=args.mode,
            all_tasks=tasks,
            selected=selected,
            judgment_path=judgments_path,
            attempt_counts=attempt_counts,
            failure_counts=failure_counts,
            duplicate_valid=duplicate_valid,
        )
    if interrupted:
        raise SystemExit(130)
    final_completed, _ = latest_valid_ids(judgments_path, task_map)
    selected_missing = sorted({row["audit_id"] for row in selected} - final_completed)
    if selected_missing:
        raise SystemExit(f"Run incomplete: {len(selected_missing)} selected audit IDs remain missing")
    print(f"COMPLETE mode={args.mode} valid={len(selected)} completion_report={completion_path}", flush=True)


if __name__ == "__main__":
    main()
