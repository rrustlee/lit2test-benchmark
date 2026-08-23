#!/usr/bin/env python3
"""Gemini (non-participant) judge for the NATIVE lit2test v0.2 blind pairwise tasks.

Reuses the EXACT native judge prompt from run_lit2test_v02_pairwise.py so the
verdicts are directly comparable to the existing judges_gpt52 outputs; only the
API transport is swapped to the Gemini /responses endpoint. Writes the native
judgment schema and is resume-capable (skips already-completed pair_ids).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests


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


def build_prompt(task: dict[str, Any]) -> str:
    # VERBATIM copy of run_lit2test_v02_pairwise.py build_prompt (native GPT-judge prompt).
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


def call_gemini_responses(api_key: str, base_url: str, model: str, prompt: str, timeout: float) -> str:
    response = requests.post(
        base_url.rstrip("/") + "/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "stream": False,
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return normalize_content(payload.get("candidates", [{}])[0].get("content", {}).get("parts", []))


def main() -> None:
    parser = argparse.ArgumentParser(description="Native-prompt Gemini pairwise judge for lit2test v0.2 blind tasks")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--judge-model", default="Gemini-3.1-Pro-Preview-Third")
    parser.add_argument("--base-url", default=os.environ.get("GEMINI_BASE_URL", "${API_BASE_URL}"))
    parser.add_argument("--api-key", default=os.environ.get("API_KEY"))
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Missing API key. Set API_KEY or pass --api-key.")

    tasks = read_jsonl(Path(args.tasks))
    if args.limit:
        tasks = tasks[: args.limit]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "pairwise_judgments.jsonl"
    raw_output = out_dir / "raw_pairwise_judgments.jsonl"
    if args.overwrite:
        output.write_text("", encoding="utf-8")
        raw_output.write_text("", encoding="utf-8")
    completed = set()
    if output.exists() and not args.overwrite:
        completed = {
            row.get("pair_id")
            for row in read_jsonl(output)
            if row.get("winner") in {"A", "B", "tie"} and not row.get("judge_errors")
        }
    pending = [row for row in tasks if row["pair_id"] not in completed]
    print(f"tasks={len(tasks)} completed={len(completed)} pending={len(pending)} out={output}", flush=True)

    for task in pending:
        pair_id = task["pair_id"]
        print(f"Gemini judging {pair_id}", flush=True)
        raw_text = ""
        try:
            raw_text = call_gemini_responses(args.api_key, args.base_url, args.judge_model, build_prompt(task), args.timeout)
            append_jsonl(raw_output, {"pair_id": pair_id, "judge_model": args.judge_model, "raw_text": raw_text})
            parsed = extract_json_object(raw_text)
            winner = str(parsed.get("winner", "")).strip()
            errors = []
            if winner not in {"A", "B", "tie"}:
                errors.append("invalid winner")
            winning_system = task["system_a"] if winner == "A" else task["system_b"] if winner == "B" else None
            row = {
                "pair_id": pair_id,
                "context_id": task["context_id"],
                "judge_model": args.judge_model,
                "system_a": task["system_a"],
                "system_b": task["system_b"],
                "winner": winner,
                "winning_system": winning_system,
                "confidence": parsed.get("confidence"),
                "main_reason": parsed.get("main_reason"),
                "weakness_a": parsed.get("weakness_a"),
                "weakness_b": parsed.get("weakness_b"),
                "judge_errors": errors,
            }
        except Exception as exc:  # noqa: BLE001 - keep the batch alive, preserve the failure.
            row = {
                "pair_id": pair_id,
                "context_id": task["context_id"],
                "judge_model": args.judge_model,
                "system_a": task["system_a"],
                "system_b": task["system_b"],
                "winner": None,
                "winning_system": None,
                "confidence": None,
                "main_reason": None,
                "weakness_a": None,
                "weakness_b": None,
                "judge_errors": [f"{type(exc).__name__}: {exc}"],
                "raw_text": raw_text,
            }
        append_jsonl(output, row)
        if args.sleep:
            time.sleep(args.sleep)
    print(f"DONE {output}", flush=True)


if __name__ == "__main__":
    main()
