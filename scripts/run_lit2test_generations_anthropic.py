#!/usr/bin/env python3
"""Run Lit2Test contexts against an Anthropic /v1/messages API.

This is a thin transport-only variant of run_lit2test_generations.py (pipeline A).
It reuses ALL of pipeline A's body logic verbatim by importing that module:
the same prompt template + build_prompt, the same messages payload
([{"role": "user", "content": prompt}], no system), the same temperature /
max_tokens, the same JSON extraction, schema validation, output format and
report writer. The ONLY difference is the call layer: OpenAI
client.chat.completions.create -> Anthropic client.messages.create.

Do NOT alter the request body here. If pipeline A changes, this inherits it.
"""

from __future__ import annotations

import argparse
import os
import signal
import time
from pathlib import Path
from typing import Any

from anthropic import Anthropic

# Reuse pipeline A's body logic verbatim.
import run_lit2test_generations as genA
from run_lit2test_generations import (
    read_jsonl,
    append_jsonl,
    normalize_content,
    extract_json_object,
    validate_payload,
    build_prompt,
    write_report,
    RequestTimeout,
    _raise_timeout,
)


def call_messages(
    client: Anthropic,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> str:
    """Anthropic transport. Body is identical to pipeline A's call_chat:
    a single user message carrying the exact same prompt, same temperature,
    same max_tokens. Only the API surface differs."""
    response = client.messages.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    # Anthropic returns content as a list of blocks; concatenate text blocks.
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(normalize_content(block))
    return "\n".join(p for p in parts if p)


def call_messages_with_outer_timeout(
    client: Anthropic,
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
        return call_messages(client, model, prompt, temperature, max_tokens, timeout)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Lit2Test context generation (Anthropic transport)")
    parser.add_argument("--contexts", default="data/lit2test_v02_expansion40_adjudicated40_contexts.jsonl")
    parser.add_argument("--template", default="prompts/lit2test_generation_prompt.md")
    parser.add_argument("--output-dir", default="outputs/lit2test_v02_expansion40_full/generations_sonnet46")
    parser.add_argument("--model", default="Claude-Sonnet-4.6-hq")
    parser.add_argument("--base-url", default=os.environ.get("ANTHROPIC_BASE_URL", "${API_BASE_URL_ANTHROPIC}"))
    parser.add_argument("--api-key", default=os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"))
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
        raise SystemExit("Missing API key. Set ANTHROPIC_AUTH_TOKEN or pass --api-key.")

    output_dir.mkdir(parents=True, exist_ok=True)
    client = Anthropic(api_key=args.api_key, base_url=args.base_url)
    attempted = 0
    succeeded = 0
    failures: list[dict[str, str]] = []
    for context in pending:
        context_id = context["context_id"]
        attempted += 1
        prompt = build_prompt(template, context)
        print(f"Running {args.model} on {context_id}", flush=True)
        try:
            raw_text = call_messages_with_outer_timeout(client, args.model, prompt, args.temperature, args.max_tokens, args.timeout)
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
    report_json_path.write_text(genA.json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Lit2Test generation status: {report['status']} succeeded={succeeded} failed={len(failures)} total_rows={total_rows}", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
