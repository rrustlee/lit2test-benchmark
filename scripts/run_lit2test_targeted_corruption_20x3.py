#!/usr/bin/env python3
"""Run the frozen 120-request Gemini targeted-corruption audit with resume."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests

from run_lit2test_dimension_decomposed_gemini_audit import (
    append_jsonl,
    extract_response_text,
    mechanical_fields,
    now_iso,
    parse_model_json,
    render_prompt,
    validate_parsed,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs/lit2test_targeted_corruption_20x3"
ENDPOINT = os.environ.get("JUDGE_BASE_URL", "${API_BASE_URL}") + "/responses"
MODEL = "Gemini-3.1-Pro-Preview-Third"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_valid(path: Path, task_map: dict[str, dict[str, Any]]) -> tuple[set[str], Counter[str]]:
    counts: Counter[str] = Counter()
    for row in read_jsonl(path):
        aid = row.get("audit_id")
        if aid not in task_map:
            raise ValueError(f"judgment references unknown audit_id {aid!r}")
        if validate_parsed(row.get("judgment"), task_map[aid]):
            raise ValueError(f"stored judgment is invalid for {aid}")
        counts[aid] += 1
    return set(counts), counts


def write_completion(path: Path, tasks: list[dict[str, Any]], judgments: Path, attempts: Counter[str], failures: Counter[str], selected: list[dict[str, Any]], mode: str) -> None:
    task_map = {row["audit_id"]: row for row in tasks}
    completed, counts = latest_valid(judgments, task_map)
    selected_ids = {row["audit_id"] for row in selected}
    report = {
        "updated_at": now_iso(),
        "mode": mode,
        "status": "complete" if selected_ids <= completed else "incomplete",
        "expected_tasks": len(tasks),
        "selected_tasks": len(selected),
        "selected_valid": len(selected_ids & completed),
        "selected_missing": sorted(selected_ids - completed),
        "all_valid": len(completed),
        "all_missing": sorted(set(task_map) - completed),
        "attempts_this_invocation": sum(attempts.values()),
        "attempts_by_audit_id_this_invocation": dict(sorted(attempts.items())),
        "failure_reasons_this_invocation": dict(sorted(failures.items())),
        "stored_valid_records": sum(counts.values()),
        "duplicate_valid_records": {aid: count for aid, count in counts.items() if count > 1},
        "completion_gate_120": len(tasks) == 120 and len(completed) == 120,
        "judge_model": MODEL,
        "endpoint": ENDPOINT,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--sleep", type=float, default=0.8)
    parser.add_argument("--backoff-base", type=float, default=2.0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out = Path(args.output_dir).resolve()
    protocol = read_json(out / "protocol.json")
    task_path = out / "audit_tasks.jsonl"
    prompt_path = out / "prompt.txt"
    if protocol.get("judge", {}).get("endpoint") != ENDPOINT:
        raise SystemExit("protocol endpoint mismatch")
    if protocol.get("judge", {}).get("model") != MODEL:
        raise SystemExit("protocol model mismatch")
    if protocol.get("files", {}).get("audit_tasks_sha256") != sha256_file(task_path):
        raise SystemExit("audit_tasks hash mismatch")
    if protocol.get("files", {}).get("prompt_sha256") != sha256_file(prompt_path):
        raise SystemExit("prompt hash mismatch")
    review = read_json(out / "independent_review_report.json")
    if review.get("status") != "pass":
        raise SystemExit("independent no-API review is not pass")

    tasks = read_jsonl(task_path)
    if len(tasks) != 120:
        raise SystemExit(f"expected 120 tasks, found {len(tasks)}")
    task_map = {row["audit_id"]: row for row in tasks}
    prompt_template = prompt_path.read_text(encoding="utf-8")
    rendered = {row["audit_id"]: render_prompt(prompt_template, row) for row in tasks}
    judgments_path = out / "judgments.jsonl"
    raw_path = out / "raw_judgments.jsonl"
    log_path = out / "run_log.jsonl"
    completion_path = out / "completion_report.json"
    completed, stored_counts = latest_valid(judgments_path, task_map)
    selected = tasks if args.mode == "full" else [task_map[aid] for aid in protocol.get("smoke_audit_ids", [])]
    if args.mode == "smoke" and len(selected) != 4:
        # deterministic smoke: first pair in each of two dimensions, both orders
        selected = [row for row in tasks if row["pair_id"] in {"pair_001", "pair_002"}]
    if args.shard_count < 1 or not 0 <= args.shard_index < args.shard_count:
        raise SystemExit("invalid shard settings")
    if args.mode == "full" and args.shard_count > 1:
        selected = [row for index, row in enumerate(selected) if index % args.shard_count == args.shard_index]
    pending = [row for row in selected if row["audit_id"] not in completed]
    print(f"mode={args.mode} selected={len(selected)} completed={len(selected)-len(pending)} pending={len(pending)} model={MODEL} endpoint={ENDPOINT}", flush=True)
    attempts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    if args.dry_run:
        write_completion(completion_path, tasks, judgments_path, attempts, failures, selected, args.mode)
        print("DRY RUN: no API requests sent", flush=True)
        return
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise SystemExit("Missing API_KEY environment variable; no API request was sent")
    rng = random.Random(int(protocol.get("selection_seed", 20260721)))
    session = requests.Session()
    interrupted = False
    try:
        for index, task in enumerate(pending):
            aid = task["audit_id"]
            succeeded = False
            for attempt in range(1, args.max_attempts + 1):
                attempts[aid] += 1
                started = time.monotonic()
                raw_text = ""
                response_body = ""
                status_code = None
                error_type = None
                error_message = None
                validation_errors: list[str] = []
                normalization = None
                valid_row = None
                try:
                    response = session.post(
                        ENDPOINT,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": MODEL, "stream": False, "contents": [{"role": "user", "parts": [{"text": rendered[aid]}]}]},
                        timeout=args.timeout,
                    )
                    status_code = response.status_code
                    response_body = response.text
                    if status_code >= 400:
                        error_type = f"http_{status_code}"
                        error_message = response_body[:1000]
                    else:
                        payload = response.json()
                        raw_text = extract_response_text(payload)
                        parsed, normalization = parse_model_json(raw_text)
                        validation_errors = validate_parsed(parsed, task)
                        if validation_errors:
                            error_type = "schema_validation_error"
                            error_message = "; ".join(validation_errors)
                        else:
                            valid_row = {
                                "audit_id": aid,
                                "case_id": task["case_id"],
                                "pair_id": task["pair_id"],
                                "order": task["order"],
                                "source_type": task["source_type"],
                                "judge_model": MODEL,
                                "attempt": attempt,
                                "validated_at": now_iso(),
                                "format_normalization": normalization,
                                "judgment": parsed,
                                **mechanical_fields(parsed),
                            }
                            succeeded = True
                except json.JSONDecodeError as exc:
                    error_type = "json_decode_error"
                    error_message = str(exc)
                except (requests.RequestException, ValueError) as exc:
                    error_type = type(exc).__name__
                    error_message = str(exc)
                except Exception as exc:
                    error_type = type(exc).__name__
                    error_message = str(exc)
                elapsed = round(time.monotonic() - started, 3)
                append_jsonl(raw_path, {"timestamp": now_iso(), "audit_id": aid, "attempt": attempt, "judge_model": MODEL, "http_status": status_code, "elapsed_seconds": elapsed, "response_body": response_body, "model_output_text": raw_text, "error_type": error_type, "error_message": error_message, "validation_errors": validation_errors, "format_normalization": normalization})
                if valid_row is not None:
                    append_jsonl(judgments_path, valid_row)
                append_jsonl(log_path, {"timestamp": now_iso(), "audit_id": aid, "attempt": attempt, "status": "valid" if succeeded else "failed", "http_status": status_code, "elapsed_seconds": elapsed, "error_type": error_type, "retry_scheduled": not succeeded and attempt < args.max_attempts})
                if succeeded:
                    print(f"VALID {aid} attempt={attempt} elapsed={elapsed}s", flush=True)
                    break
                failures[error_type or "unknown_error"] += 1
                print(f"FAILED {aid} attempt={attempt}/{args.max_attempts} type={error_type} elapsed={elapsed}s", flush=True)
                if attempt < args.max_attempts:
                    time.sleep(args.backoff_base * (2 ** (attempt - 1)) + rng.uniform(0, 0.2))
            if args.sleep and index + 1 < len(pending):
                time.sleep(args.sleep)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        write_completion(completion_path, tasks, judgments_path, attempts, failures, selected, args.mode)
    if interrupted:
        raise SystemExit(130)
    final_completed, _ = latest_valid(judgments_path, task_map)
    missing = sorted({row["audit_id"] for row in selected} - final_completed)
    if missing:
        raise SystemExit(f"Run incomplete: {len(missing)} selected tasks remain missing")
    print(f"COMPLETE mode={args.mode} valid={len(selected)} completion_report={completion_path}", flush=True)


if __name__ == "__main__":
    main()
