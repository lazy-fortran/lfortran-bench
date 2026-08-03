from __future__ import annotations

import json
import subprocess
from pathlib import Path


JUDGE_KEYS = {
    "overall_score",
    "correctness",
    "maintainability",
    "minimality",
    "issue_fit",
    "verification",
    "summary",
    "findings",
}


def validate_judge_result(result: dict) -> str | None:
    if set(result.keys()) != JUDGE_KEYS:
        return f"expected keys {sorted(JUDGE_KEYS)}, got {sorted(result.keys())}"
    for key in ["overall_score", "correctness", "maintainability", "minimality", "issue_fit", "verification"]:
        value = result.get(key)
        if not isinstance(value, int) or not (1 <= value <= 5):
            return f"{key} must be an integer from 1 to 5"
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        return "summary must be a non-empty string"
    findings = result.get("findings")
    if not isinstance(findings, list) or len(findings) > 3:
        return "findings must be a list with at most 3 items"
    if any(not isinstance(item, str) or not item.strip() for item in findings):
        return "each finding must be a non-empty string"
    return None


def judge_prompt(task: dict, final_stage: dict, acceptance: dict, retry_error: str | None = None, previous_output: str | None = None) -> str:
    compact_acceptance = {
        "ok": acceptance.get("ok"),
        "command_results": [
            {
                "command": item.get("command"),
                "returncode": item.get("returncode"),
                "stdout": (item.get("stdout") or "")[:2000],
                "stderr": (item.get("stderr") or "")[:2000],
                "duration_seconds": item.get("duration_seconds"),
                "ok": item.get("ok"),
            }
            for item in acceptance.get("command_results", [])
        ],
    }
    compact_final_stage = {
        "stage": final_stage.get("stage"),
        "agent_ok": final_stage.get("agent_ok"),
        "agent_error": final_stage.get("agent_error"),
        "agent_duration_seconds": final_stage.get("agent_duration_seconds"),
        "agent_text": (final_stage.get("agent_text") or "")[:12000],
        "setup_results": [
            {
                "command": item.get("command"),
                "returncode": item.get("returncode"),
                "stdout": (item.get("stdout") or "")[:1000],
                "stderr": (item.get("stderr") or "")[:1000],
                "duration_seconds": item.get("duration_seconds"),
                "ok": item.get("ok"),
            }
            for item in final_stage.get("setup_results", [])
        ],
        "acceptance_ok": final_stage.get("acceptance_ok"),
    }
    retry_block = ""
    if retry_error:
        retry_block = f"""

Your previous response was invalid.

Validation error:
{retry_error}

Previous response:
{previous_output or ""}
"""
    return f"""You are grading a Fortran coding benchmark run.

Task id: {task["id"]}
Issue: {task["issue_url"]}
Title: {task["title"]}

Scoring rubric:
- correctness: does the patch actually satisfy the issue behavior and the observed acceptance evidence?
- maintainability: is the change understandable and unlikely to create future maintenance debt?
- minimality: does the patch avoid unnecessary churn or unrelated changes?
- issue_fit: does it solve the intended issue rather than only gaming the validator?
- verification: does the final-stage evidence show adequate local verification for the claim?
- overall_score: holistic score, weighted primarily by correctness and issue_fit.

Scoring scale:
- 5 = excellent
- 4 = good
- 3 = mixed / partial
- 2 = weak
- 1 = poor

Acceptance summary:
{json.dumps(compact_acceptance, indent=2)}

Final stage summary:
{json.dumps(compact_final_stage, indent=2)}

Return exactly one JSON object with no markdown and no extra keys.
Use this exact schema:
{{
  "overall_score": 1,
  "correctness": 1,
  "maintainability": 1,
  "minimality": 1,
  "issue_fit": 1,
  "verification": 1,
  "summary": "short paragraph",
  "findings": ["finding 1", "finding 2"]
}}

Rules:
- All numeric fields must be integers from 1 to 5.
- `findings` must contain at most 3 short strings.
- If the run is strong, `findings` may be an empty list.
- Do not rename keys.
- Do not add keys.
- Do not wrap the JSON in code fences.
{retry_block}
"""


def run_claude_judge(task: dict, final_stage: dict, acceptance: dict, cwd: Path) -> dict:
    schema = json.dumps(
        {
            "type": "object",
            "properties": {
                "overall_score": {"type": "integer", "minimum": 1, "maximum": 5},
                "correctness": {"type": "integer", "minimum": 1, "maximum": 5},
                "maintainability": {"type": "integer", "minimum": 1, "maximum": 5},
                "minimality": {"type": "integer", "minimum": 1, "maximum": 5},
                "issue_fit": {"type": "integer", "minimum": 1, "maximum": 5},
                "verification": {"type": "integer", "minimum": 1, "maximum": 5},
                "summary": {"type": "string"},
                "findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
            },
            "required": [
                "overall_score",
                "correctness",
                "maintainability",
                "minimality",
                "issue_fit",
                "verification",
                "summary",
                "findings",
            ],
            "additionalProperties": False,
        }
    )
    prompt = judge_prompt(task, final_stage, acceptance)
    try:
        proc = subprocess.run(
            [
                "claude",
                "--print",
                "--output-format",
                "json",
                "--json-schema",
                schema,
                "--dangerously-skip-permissions",
                "--model",
                "opus",
                prompt,
            ],
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=300,
        )
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "judge timed out after 300 seconds"}
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip() or proc.stdout.strip()}
    raw = proc.stdout.strip()
    try:
        parsed_envelope = json.loads(raw)
    except Exception:
        return {"ok": False, "error": "response was not valid JSON", "raw": raw}
    parsed = parsed_envelope.get("structured_output")
    if not isinstance(parsed, dict):
        return {"ok": False, "error": "missing structured_output in claude judge response", "raw": raw}
    validation_error = validate_judge_result(parsed)
    if validation_error is not None:
        return {"ok": False, "error": validation_error, "raw": raw}
    return {"ok": True, "result": parsed}


def run_codex_judge(task: dict, final_stage: dict, acceptance: dict, cwd: Path) -> dict:
    retry_error = None
    previous_output = None
    for _ in range(2):
        prompt = judge_prompt(task, final_stage, acceptance, retry_error=retry_error, previous_output=previous_output)
        try:
            proc = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--json",
                    "--dangerously-bypass-approvals-and-sandbox",
                    "--model",
                    "gpt-5.4",
                    prompt,
                ],
                cwd=str(cwd),
                text=True,
                capture_output=True,
                timeout=300,
            )
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "judge timed out after 300 seconds"}
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or proc.stdout.strip()}
        last = None
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except Exception:
                continue
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                last = item.get("text")
        if not last:
            return {"ok": False, "error": "missing codex judge output"}
        try:
            parsed = json.loads(last)
        except Exception:
            retry_error = "response was not valid JSON"
            previous_output = last
            continue
        validation_error = validate_judge_result(parsed)
        if validation_error is None:
            return {"ok": True, "result": parsed}
        retry_error = validation_error
        previous_output = json.dumps(parsed, indent=2)
    return {"ok": False, "error": f"invalid codex judge output after retry: {retry_error}", "raw": previous_output}
