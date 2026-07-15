from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentResponse:
    ok: bool
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    text: str
    error: str | None = None


TERMINATION_GRACE_SECONDS = 2


def _terminate_process(proc: subprocess.Popen) -> tuple[str, str]:
    """Terminate a process group without waiting forever for cooperative exit."""
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        return proc.communicate(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        return proc.communicate()


def _workspace_progress_signature(cwd: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    diff = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--", "."],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    return json.dumps({"status": status.stdout, "diff": diff.stdout}, sort_keys=True)


def _run_command(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
    stagnation_seconds: int | None = None,
) -> AgentResponse:
    started = time.time()
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    last_progress = time.time()
    last_signature = _workspace_progress_signature(cwd) if stagnation_seconds else None
    deadline = started + timeout_seconds
    while True:
        remaining = max(0.0, deadline - time.time())
        if remaining <= 0:
            stdout, stderr = _terminate_process(proc)
            duration = time.time() - started
            return AgentResponse(
                ok=False,
                command=command,
                returncode=124,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                text=_extract_text(command[0], stdout, stderr),
                error=f"timed out after {timeout_seconds} seconds",
            )
        try:
            stdout, stderr = proc.communicate(timeout=min(5, remaining))
            duration = time.time() - started
            return AgentResponse(
                ok=proc.returncode == 0,
                command=command,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                text=_extract_text(command[0], stdout, stderr),
                error=None if proc.returncode == 0 else f"command failed with exit code {proc.returncode}",
            )
        except subprocess.TimeoutExpired:
            if stagnation_seconds:
                current_signature = _workspace_progress_signature(cwd)
                if current_signature != last_signature:
                    last_signature = current_signature
                    last_progress = time.time()
                elif time.time() - last_progress >= stagnation_seconds:
                    stdout, stderr = _terminate_process(proc)
                    duration = time.time() - started
                    return AgentResponse(
                        ok=False,
                        command=command,
                        returncode=124,
                        stdout=stdout,
                        stderr=stderr,
                        duration_seconds=duration,
                        text=_extract_text(command[0], stdout, stderr),
                        error=f"stagnated for {stagnation_seconds} seconds without workspace changes",
                    )


def _extract_text(agent: str, stdout: str, stderr: str) -> str:
    if agent == "opencode":
        try:
            last = None
            for line in stdout.splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("type") == "text":
                    last = event["part"]["text"]
                elif event.get("type") == "result":
                    last = event.get("result", last)
            return last or stdout.strip()
        except Exception:
            return stdout.strip() or stderr.strip()
    if agent == "qwen":
        try:
            events = json.loads(stdout)
            last = ""
            for event in events:
                if event.get("type") == "assistant":
                    content = event.get("message", {}).get("content", [])
                    for part in content:
                        if part.get("type") == "text":
                            last = part.get("text", last)
                elif event.get("type") == "result":
                    last = event.get("result", last)
            return last or stdout.strip()
        except Exception:
            return stdout.strip() or stderr.strip()
    if agent == "claude":
        try:
            payload = json.loads(stdout)
            return payload.get("result", stdout.strip())
        except Exception:
            return stdout.strip() or stderr.strip()
    if agent == "codex":
        last = ""
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                last = item.get("text", last)
        return last or stdout.strip() or stderr.strip()
    return stdout.strip() or stderr.strip()


class BaseAdapter:
    name: str

    def stage(self, stage_index: int, prompt: str, workspace: Path, run_dir: Path, row: dict, timeout_seconds: int) -> AgentResponse:
        raise NotImplementedError


class OpenCodeAdapter(BaseAdapter):
    name = "opencode"

    def stage(self, stage_index: int, prompt: str, workspace: Path, run_dir: Path, row: dict, timeout_seconds: int) -> AgentResponse:
        command = [
            "opencode",
            "run",
            "--dir",
            str(workspace),
            "--format",
            "json",
        ]
        model = row.get("model")
        if model:
            command.extend(["--model", model])
        variant = row.get("variant")
        if variant:
            command.extend(["--variant", variant])
        command.append(prompt)
        return _run_command(command, workspace, timeout_seconds, stagnation_seconds=row.get("stagnation_seconds"))


class QwenCodeAdapter(BaseAdapter):
    name = "qwen"

    def stage(self, stage_index: int, prompt: str, workspace: Path, run_dir: Path, row: dict, timeout_seconds: int) -> AgentResponse:
        command = [
            "qwen",
            "--approval-mode",
            "yolo",
            "--output-format",
            "json",
        ]
        model = row.get("model")
        if model:
            command.extend(["--model", model])
        openai_base_url = row.get("openai_base_url")
        if openai_base_url:
            command.extend(["--openai-base-url", openai_base_url, "--openai-api-key", row.get("openai_api_key", "dummy")])
        command.append(prompt)
        return _run_command(command, workspace, timeout_seconds, stagnation_seconds=row.get("stagnation_seconds"))


class ClaudeCodeAdapter(BaseAdapter):
    name = "claude"

    def stage(self, stage_index: int, prompt: str, workspace: Path, run_dir: Path, row: dict, timeout_seconds: int) -> AgentResponse:
        command = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
        ]
        model = row.get("model")
        if model:
            command.extend(["--model", model])
        effort = row.get("effort")
        if effort:
            command.extend(["--effort", effort])
        command.append(prompt)
        return _run_command(command, workspace, timeout_seconds, stagnation_seconds=row.get("stagnation_seconds"))


class CodexAdapter(BaseAdapter):
    name = "codex"

    def stage(self, stage_index: int, prompt: str, workspace: Path, run_dir: Path, row: dict, timeout_seconds: int) -> AgentResponse:
        command = ["codex"]
        profile = row.get("profile")
        if profile:
            command.extend(["-p", profile])
        model_provider = row.get("model_provider")
        if model_provider:
            command.extend(["-c", f'model_provider="{model_provider}"'])
        command.extend([
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--cd",
            str(workspace),
        ])
        model = row.get("model")
        if model:
            command.extend(["--model", model])
        command.append("--")
        command.append(prompt)
        return _run_command(command, workspace, timeout_seconds, stagnation_seconds=row.get("stagnation_seconds"))


class AiderAdapter(BaseAdapter):
    name = "aider"

    def stage(self, stage_index: int, prompt: str, workspace: Path, run_dir: Path, row: dict, timeout_seconds: int) -> AgentResponse:
        history = run_dir / "aider.chat.history.md"
        command = [
            "aider",
            "--yes-always",
            "--no-pretty",
            "--no-fancy-input",
            "--no-auto-commits",
            "--no-dirty-commits",
            "--no-show-model-warnings",
            "--no-check-model-accepts-settings",
            "--message",
            prompt,
            "--exit",
            "--chat-history-file",
            str(history),
        ]
        model = row.get("model") or "openai/qwen"
        command.extend(["--model", model])
        api_base = row.get("openai_api_base")
        if api_base:
            command.extend(["--openai-api-base", api_base, "--openai-api-key", row.get("openai_api_key", "dummy")])
        return _run_command(command, workspace, timeout_seconds, stagnation_seconds=row.get("stagnation_seconds"))


def build_adapter(name: str) -> BaseAdapter:
    mapping = {
        "opencode": OpenCodeAdapter,
        "aider": AiderAdapter,
        "qwen": QwenCodeAdapter,
        "claude": ClaudeCodeAdapter,
        "codex": CodexAdapter,
    }
    adapter_cls = mapping.get(name)
    if adapter_cls is None:
        raise ValueError(f"unsupported adapter: {name}")
    return adapter_cls()
