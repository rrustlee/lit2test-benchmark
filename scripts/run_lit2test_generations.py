#!/usr/bin/env python3
"""Run Lit2Test contexts against an OpenAI-compatible chat API."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import time
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
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
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


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
        if "content" in content:
            return normalize_content(content["content"])
        return json.dumps(content, ensure_ascii=False)
    if isinstance(content, list):
        return "\n".join(normalize_content(item) for item in content if normalize_content(item))
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


def validate_payload(payload: dict[str, Any], context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if not str(payload.get(field, "")).strip():
            errors.append(f"missing {field}")
    if payload.get("context_id") and payload.get("context_id") != context.get("context_id"):
        errors.append(f"context_id mismatch: {payload.get('context_id')} != {context.get('context_id')}")
    if payload.get("condition") and payload.get("condition") != context.get("condition"):
        errors.append(f"condition mismatch: {payload.get('condition')} != {context.get('condition')}")
    return errors


def build_prompt(template: str, context: dict[str, Any]) -> str:
    return template.replace("{{LIT2TEST_CONTEXT_JSON}}", json.dumps(context, ensure_ascii=False, indent=2))


def call_chat(client: OpenAI, model: str, prompt: str, temperature: float, max_tokens: int, timeout: float) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return normalize_content(response.choices[0].message.content)


class RequestTimeout(RuntimeError):
    pass


def _raise_timeout(signum: int, frame: Any) -> None:  # noqa: ARG001 - signal handler signature.
    raise RequestTimeout("outer request timeout")


def call_chat_with_outer_timeout(
    client: OpenAI,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> str:
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return call_chat(client, model, prompt, temperature, max_tokens, timeout)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def write_report(report_path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Lit2Test Generation Run Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Policy: `{report['policy']}`",
        f"- Model: `{report['model']}`",
        f"- Contexts requested: {report['contexts_requested']}",
        f"- Completed before run: {report['completed_before_run']}",
        f"- Attempted this run: {report['attempted_this_run']}",
        f"- Succeeded this run: {report['succeeded_this_run']}",
        f"- Failed this run: {report['failed_this_run']}",
        f"- Parsed output rows total: {report['parsed_output_rows_total']}",
        f"- Output dir: `{report['output_dir']}`",
        f"- Release ready: `{report['release_ready']}`",
        f"- Allowed to publish leaderboard: `{report['allowed_to_publish_leaderboard']}`",
        "",
        "## Failures",
        "",
    ]
    if report["failures"]:
        for failure in report["failures"]:
            lines.append(f"- `{failure['context_id']}`: {failure['error']}")
    else:
        lines.append("None.")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Lit2Test context generation")
    parser.add_argument("--contexts", default="data/lit2test_perturbation_probe_8x3.jsonl")
    parser.add_argument("--template", default="prompts/lit2test_generation_prompt.md")
    parser.add_argument("--output-dir", default="outputs/lit2test_perturbation_probe_8x3/generations_gpt52")
    parser.add_argument("--model", default="GPT 5.2")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "${API_BASE_URL}"))
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    contexts = read_jsonl(Path(args.contexts))
    if args.limit is not None:
        contexts = contexts[: args.limit]
    template = Path(args.template).read_text(encoding="utf-8")
    output_dir = Path(args.output_dir)
    parsed_path = output_dir / "lit2test_outputs.jsonl"
    raw_path = output_dir / "raw_responses.jsonl"
    report_path = output_dir / "run_report.md"
    report_json_path = output_dir / "run_report.json"
    completed = set()
    if parsed_path.exists():
        completed = {row.get("context_id") for row in read_jsonl(parsed_path) if row.get("context_id")}

    pending = [context for context in contexts if context.get("context_id") not in completed]
    if args.dry_run:
        print(f"DRY RUN model={args.model} pending={len(pending)} completed={len(completed)}")
        for context in pending:
            print(context["context_id"], context["condition"])
        return

    if not args.api_key:
        raise SystemExit("Missing API key. Set OPENAI_API_KEY or pass --api-key.")

    output_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    attempted = 0
    succeeded = 0
    failures: list[dict[str, str]] = []
    for context in pending:
        context_id = context["context_id"]
        attempted += 1
        prompt = build_prompt(template, context)
        print(f"Running {args.model} on {context_id}", flush=True)
        try:
            raw_text = call_chat_with_outer_timeout(client, args.model, prompt, args.temperature, args.max_tokens, args.timeout)
            raw_row = {
                "context_id": context_id,
                "condition": context.get("condition"),
                "model": args.model,
                "raw_text": raw_text,
            }
            append_jsonl(raw_path, raw_row)
            payload = extract_json_object(raw_text)
            payload.setdefault("context_id", context_id)
            payload.setdefault("condition", context.get("condition"))
            schema_errors = validate_payload(payload, context)
            row = {**payload, "model": args.model, "schema_errors": schema_errors}
            append_jsonl(parsed_path, row)
            if schema_errors:
                failures.append({"context_id": context_id, "error": "; ".join(schema_errors)})
            else:
                succeeded += 1
        except Exception as exc:  # noqa: BLE001 - preserve failure in report and continue.
            failures.append({"context_id": context_id, "error": repr(exc)})
            append_jsonl(raw_path, {"context_id": context_id, "condition": context.get("condition"), "model": args.model, "error": repr(exc)})
        if args.sleep > 0:
            time.sleep(args.sleep)

    total_rows = len(read_jsonl(parsed_path)) if parsed_path.exists() else 0
    report = {
        "status": "pass" if not failures else "partial_or_failed",
        "policy": "bounded_serial_lit2test_generation_no_leaderboard_no_release",
        "model": args.model,
        "contexts_requested": len(contexts),
        "completed_before_run": len(completed),
        "attempted_this_run": attempted,
        "succeeded_this_run": succeeded,
        "failed_this_run": len(failures),
        "parsed_output_rows_total": total_rows,
        "output_dir": str(output_dir),
        "failures": failures,
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
    }
    write_report(report_path, report)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Lit2Test generation status: {report['status']} succeeded={succeeded} failed={len(failures)} total_rows={total_rows}", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
