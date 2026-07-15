from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from lfortran_bench.adapters import AgentResponse, build_adapter
from lfortran_bench.judges import run_claude_judge, run_codex_judge

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVSTRAL_SCRIPTS = REPO_ROOT.parent / "devstral-infra" / "scripts"


@dataclass
class AcceptanceResult:
    ok: bool
    command_results: list[dict]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def render_command(template: str, workspace: Path, task_dir: Path) -> str:
    return template.format(workspace=workspace, task_dir=task_dir)


def run_shell(command: str, cwd: Path, timeout_seconds: int = 600) -> dict:
    started = time.time()
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_seconds": round(time.time() - started, 2),
        "ok": proc.returncode == 0,
    }


def clone_workspace(task: dict, workspace: Path) -> None:
    clone_workspace_at(task["repo_url"], task["base_commit"], workspace)


def clone_workspace_at(repo_url: str, commit: str, workspace: Path) -> None:
    subprocess.run(["git", "clone", repo_url, str(workspace)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "fetch", "origin", commit], cwd=str(workspace), check=False, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "-f", commit], cwd=str(workspace), check=True, capture_output=True, text=True)


def run_setup(task: dict, workspace: Path, task_dir: Path) -> list[dict]:
    results = []
    for command in task.get("setup_commands", []):
        rendered = render_command(command, workspace, task_dir)
        results.append(run_shell(rendered, workspace))
    return results


def run_acceptance(task: dict, workspace: Path, task_dir: Path) -> AcceptanceResult:
    results = []
    for command in task["acceptance_commands"]:
        rendered = render_command(command, workspace, task_dir)
        results.append(run_shell(rendered, workspace))
    return AcceptanceResult(ok=all(item["ok"] for item in results), command_results=results)


def workspace_signature(workspace: Path) -> str:
    proc = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=str(workspace),
        text=True,
        capture_output=True,
        check=False,
    )
    diff = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--", "."],
        cwd=str(workspace),
        text=True,
        capture_output=True,
        check=False,
    )
    return json.dumps(
        {
            "status": proc.stdout,
            "diff": diff.stdout,
        },
        sort_keys=True,
    )


def acceptance_signature(acceptance: AcceptanceResult) -> str:
    return json.dumps(asdict(acceptance), sort_keys=True)


def stage_prompt(task: dict, stage_index: int, acceptance: AcceptanceResult | None) -> str:
    header = f"""You are working on a frozen benchmark task in a git worktree.

Task id: {task["id"]}
Issue URL: {task["issue_url"]}
Title: {task["title"]}

Issue body:
{task["issue_body"]}

Rules:
- Do not create git commits.
- Modify only the task repository in the current working directory.
- Use local tests and commands only.
- Keep the patch minimal and aligned with the issue.
- Make the smallest plausible patch that fixes the issue and then stop.
- Do not add new tests unless the task explicitly requires them.
- Do not run the full project test suite unless the task explicitly requires it.
- Do not keep exploring, polishing, or adding extra verification after the minimal fix is in place.
- FortBench will run the deterministic acceptance checks after you exit.
- Exit immediately once you have applied the minimal plausible fix.

Acceptance rubric for this benchmark task:
{task.get("acceptance_hint", "No extra acceptance hint provided.")}
"""
    if stage_index == 1:
        return header + "\nStage 1: implement the minimal fix, explain briefly what changed, and exit immediately."
    feedback = json.dumps(asdict(acceptance), indent=2) if acceptance else "{}"
    if stage_index == 2:
        return header + f"""

Stage 2: self-review plus repair.

Use the deterministic feedback below. First critique your own work briefly, then make the smallest repair needed and exit immediately.

Acceptance feedback:
{feedback}
"""
    return header + f"""

Stage 3: final repair and polish.

Use the same quality rubric: correctness, minimality, maintainability, and clear user-facing behavior. Make only the smallest final repair needed, then exit immediately.

Acceptance feedback:
{feedback}
"""


def stage_record(stage_index: int, response: AgentResponse, setup_results: list[dict], acceptance: AcceptanceResult) -> dict:
    return {
        "stage": stage_index,
        "agent_ok": response.ok,
        "agent_error": response.error,
        "agent_text": response.text,
        "agent_stdout": response.stdout,
        "agent_stderr": response.stderr,
        "agent_command": response.command,
        "agent_duration_seconds": round(response.duration_seconds, 2),
        "setup_results": setup_results,
        "acceptance_ok": acceptance.ok,
        "acceptance": asdict(acceptance),
    }


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_markdown_summary(report_path: Path, suite: dict, run_rows: list[dict]) -> None:
    lines = [
        f"# FortBench Report: {suite['name']}",
        "",
        f"- Generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        "",
        "| Task | Agent | Budget | Final Status | Solved Stage | Runtime (s) |",
        "|---|---|---:|---|---:|---:|",
    ]
    for row in run_rows:
        lines.append(
            f"| {row['task_id']} | {row['row_name']} | {row['budget_tier']} | "
            f"{row['final_status']} | {row['solved_stage'] or '-'} | {row['runtime_seconds_total']:.2f} |"
        )
    report_path.write_text("\n".join(lines) + "\n")


def write_csv_summary(report_path: Path, run_rows: list[dict]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "task_id",
        "row_name",
        "agent",
        "model_alias",
        "budget_tier",
        "provider_class",
        "final_status",
        "solved_stage",
        "runtime_seconds_total",
        "local_model_switch_seconds",
    ]
    lines = [",".join(headers)]
    for row in run_rows:
        values = [
            str(row.get("task_id", "")),
            str(row.get("row_name", "")),
            str(row.get("agent", "")),
            str(row.get("model_alias", "")),
            str(row.get("budget_tier", "")),
            str(row.get("provider_class", "")),
            str(row.get("final_status", "")),
            str(row.get("solved_stage") or ""),
            str(row.get("runtime_seconds_total", "")),
            str(row.get("local_model_switch_seconds", "")),
        ]
        lines.append(",".join(value.replace(",", ";") for value in values))
    report_path.write_text("\n".join(lines) + "\n")


def write_suite_artifacts(output_dir: Path, suite: dict, run_rows: list[dict]) -> None:
    write_json(output_dir / "results.json", run_rows)
    write_markdown_summary(output_dir / "summary.md", suite, run_rows)
    write_csv_summary(output_dir / "summary.csv", run_rows)


def write_task_check_summary(report_path: Path, task: dict, base_setup: list[dict], base_acceptance: AcceptanceResult, fixed_setup: list[dict], fixed_acceptance: AcceptanceResult) -> None:
    lines = [
        f"# FortBench Task Check: {task['id']}",
        "",
        f"- Title: `{task['title']}`",
        f"- Repo: `{task['repo_url']}`",
        f"- Base commit: `{task['base_commit']}`",
        f"- Fixed commit: `{task['fixed_commit']}`",
        f"- Base acceptance: `{'pass' if base_acceptance.ok else 'fail'}`",
        f"- Fixed acceptance: `{'pass' if fixed_acceptance.ok else 'fail'}`",
        "",
        "## Base Commands",
        "",
    ]
    for item in [*base_setup, *base_acceptance.command_results]:
        lines.append(f"- `{item['command']}` -> `{item['returncode']}` in `{item['duration_seconds']:.2f}s`")
    lines.extend(["", "## Fixed Commands", ""])
    for item in [*fixed_setup, *fixed_acceptance.command_results]:
        lines.append(f"- `{item['command']}` -> `{item['returncode']}` in `{item['duration_seconds']:.2f}s`")
    report_path.write_text("\n".join(lines) + "\n")


def run_task_row(task: dict, row: dict, reports_dir: Path, local_model_switch_seconds: float = 0.0) -> dict:
    task_dir = Path(task["_task_dir"])
    run_id = f"{task['id']}__{row['name']}"
    run_dir = reports_dir / "artifacts" / run_id
    workspace = run_dir / "workspace"
    run_dir.mkdir(parents=True, exist_ok=True)
    clone_workspace(task, workspace)
    setup_results = run_setup(task, workspace, task_dir)
    baseline_acceptance = run_acceptance(task, workspace, task_dir)
    if baseline_acceptance.ok:
        raise RuntimeError("task baseline acceptance already passes on frozen base commit")

    adapter = build_adapter(row["adapter"])
    stage_budget_seconds = row.get("stage_budget_seconds", [600, 600, 600])
    stage_results: list[dict] = []
    acceptance: AcceptanceResult | None = None
    started = time.time()
    solved_stage = None
    previous_workspace_sig = None
    previous_acceptance_sig = None

    for idx, budget in enumerate(stage_budget_seconds, start=1):
        prompt = stage_prompt(task, idx, acceptance)
        response = adapter.stage(idx, prompt, workspace, run_dir, row, budget)
        stage_setup_results = run_setup(task, workspace, task_dir)
        acceptance = run_acceptance(task, workspace, task_dir)
        record = stage_record(idx, response, stage_setup_results, acceptance)
        stage_results.append(record)
        current_workspace_sig = workspace_signature(workspace)
        current_acceptance_sig = acceptance_signature(acceptance)
        if response.ok and acceptance.ok and solved_stage is None:
            solved_stage = idx
            break
        if (
            idx >= 2
            and solved_stage is None
            and previous_workspace_sig is not None
            and previous_acceptance_sig is not None
            and current_workspace_sig == previous_workspace_sig
            and current_acceptance_sig == previous_acceptance_sig
        ):
            break
        previous_workspace_sig = current_workspace_sig
        previous_acceptance_sig = current_acceptance_sig

    final_status = "solved" if solved_stage else "failed"
    final_stage = stage_results[-1]
    judges = {}
    if final_status == "solved" and row.get("run_judges", True):
        for judge_engine in row.get("judge_engines", ["codex"]):
            if judge_engine == "claude":
                judges["claude"] = run_claude_judge(task, final_stage, asdict(acceptance), workspace)
            elif judge_engine == "codex":
                judges["codex"] = run_codex_judge(task, final_stage, asdict(acceptance), workspace)
    result = {
        "task_id": task["id"],
        "task_title": task["title"],
        "row_name": row["name"],
        "agent": row["adapter"],
        "model_alias": row.get("model", ""),
        "budget_tier": row.get("budget_tier", "fixed/default"),
        "provider_class": row.get("provider_class", "cloud"),
        "local_model_alias": row.get("local_model_alias", ""),
        "local_model_switch_seconds": round(local_model_switch_seconds, 2),
        "setup_results": setup_results,
        "baseline_acceptance": asdict(baseline_acceptance),
        "solved_stage": solved_stage,
        "final_status": final_status,
        "runtime_seconds_total": round(time.time() - started, 2),
        "stage_results": stage_results,
        "judges": judges,
    }
    write_json(run_dir / "result.json", result)
    return result


def load_suite(path: Path) -> tuple[dict, list[dict]]:
    suite = load_yaml(path)
    task_defs = []
    for task_path in suite["tasks"]:
        full = (path.parent.parent / task_path).resolve()
        task = load_yaml(full)
        task["_task_dir"] = str(full.parent)
        task_defs.append(task)
    return suite, task_defs


def load_task(path: Path) -> dict:
    full = path.resolve()
    task = load_yaml(full)
    task["_task_dir"] = str(full.parent)
    return task


def local_model_env(row: dict) -> dict[str, str]:
    env = os.environ.copy()
    env["LLAMACPP_MODEL_ALIAS"] = row["local_model_alias"]
    instance = row.get("local_instance", "local")
    if instance == "fast":
        env["LLAMACPP_ENABLE_THINKING"] = "false"
    else:
        env.setdefault("LLAMACPP_ENABLE_THINKING", "true")
    return env


def switch_local_model(row: dict) -> float:
    if not row.get("local_model_alias"):
        return 0.0
    instance = row.get("local_instance")
    started = time.time()
    subprocess.run(
        ["bash", str(DEVSTRAL_SCRIPTS / "server_stop_llamacpp.sh"), "all"],
        check=False, capture_output=True, text=True,
    )
    start_args = ["bash", str(DEVSTRAL_SCRIPTS / "server_start_llamacpp.sh")]
    if instance:
        start_args.append(instance)
    subprocess.run(
        start_args,
        check=True,
        capture_output=True,
        text=True,
        env=local_model_env(row),
    )
    return time.time() - started


def restore_default_model(suite: dict) -> None:
    alias = suite.get("default_local_model_alias")
    if not alias:
        return
    env = os.environ.copy()
    env["LLAMACPP_MODEL_ALIAS"] = alias
    subprocess.run(["bash", str(DEVSTRAL_SCRIPTS / "server_stop_llamacpp.sh")], check=False, capture_output=True, text=True)
    subprocess.run(
        ["bash", str(DEVSTRAL_SCRIPTS / "server_start_llamacpp.sh")],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def failure_result(task: dict, row: dict, exc: Exception) -> dict:
    return {
        "task_id": task["id"],
        "task_title": task["title"],
        "row_name": row["name"],
        "agent": row["adapter"],
        "model_alias": row.get("model", ""),
        "budget_tier": row.get("budget_tier", "fixed/default"),
        "provider_class": row.get("provider_class", "cloud"),
        "local_model_alias": row.get("local_model_alias", ""),
        "local_model_switch_seconds": 0.0,
        "solved_stage": None,
        "final_status": "error",
        "runtime_seconds_total": 0.0,
        "stage_results": [],
        "error": str(exc),
        "judges": {},
    }


def run_suite(suite_path: Path, output_dir: Path, continue_on_error: bool) -> int:
    suite, tasks = load_suite(suite_path)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_rows = []
    local_rows = [row for row in suite["rows"] if row.get("provider_class") == "local"]
    cloud_rows = [row for row in suite["rows"] if row.get("provider_class") != "local"]
    cloud_workers = suite.get("cloud_parallelism", 2)
    cloud_executor: ThreadPoolExecutor | None = None
    local_executor: ThreadPoolExecutor | None = None
    future_map = {}
    local_work_items = [(task, row) for task in tasks for row in local_rows]
    next_local_index = 0

    def run_local_item(task: dict, row: dict) -> dict:
        switch_seconds = switch_local_model(row)
        return run_task_row(task, row, output_dir, local_model_switch_seconds=switch_seconds)

    def submit_next_local() -> None:
        nonlocal next_local_index
        if local_executor is None or next_local_index >= len(local_work_items):
            return
        task, row = local_work_items[next_local_index]
        next_local_index += 1
        future_map[local_executor.submit(run_local_item, task, row)] = (task, row)

    try:
        cloud_work_items = [(task, row) for task in tasks for row in cloud_rows]
        if cloud_work_items:
            cloud_executor = ThreadPoolExecutor(max_workers=cloud_workers)
            for task, row in cloud_work_items:
                future_map[cloud_executor.submit(run_task_row, task, row, output_dir)] = (task, row)

        if local_work_items:
            local_executor = ThreadPoolExecutor(max_workers=1)
            submit_next_local()

        while future_map:
            done, _ = wait(future_map.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                task, row = future_map.pop(future)
                try:
                    run_rows.append(future.result())
                    write_suite_artifacts(output_dir, suite, run_rows)
                    if row.get("provider_class") == "local":
                        submit_next_local()
                except Exception as exc:
                    run_rows.append(failure_result(task, row, exc))
                    write_suite_artifacts(output_dir, suite, run_rows)
                    if row.get("provider_class") == "local":
                        submit_next_local()
                    if not continue_on_error:
                        if cloud_executor:
                            cloud_executor.shutdown(cancel_futures=True)
                        if local_executor:
                            local_executor.shutdown(cancel_futures=True)
                        return 1
    finally:
        if local_rows:
            restore_default_model(suite)
        if cloud_executor:
            cloud_executor.shutdown(wait=True, cancel_futures=False)
        if local_executor:
            local_executor.shutdown(wait=True, cancel_futures=False)

    write_suite_artifacts(output_dir, suite, run_rows)
    return 0


def check_task(task_path: Path, output_dir: Path) -> int:
    task = load_task(task_path)
    task_dir = Path(task["_task_dir"])
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_dir = output_dir / "artifacts"
    base_dir = artifact_dir / "base-workspace"
    fixed_dir = artifact_dir / "fixed-workspace"
    if base_dir.exists():
        shutil.rmtree(base_dir)
    if fixed_dir.exists():
        shutil.rmtree(fixed_dir)

    clone_workspace_at(task["repo_url"], task["base_commit"], base_dir)
    clone_workspace_at(task["repo_url"], task["fixed_commit"], fixed_dir)

    base_setup = run_setup(task, base_dir, task_dir)
    fixed_setup = run_setup(task, fixed_dir, task_dir)
    base_acceptance = run_acceptance(task, base_dir, task_dir)
    fixed_acceptance = run_acceptance(task, fixed_dir, task_dir)

    report = {
        "task_id": task["id"],
        "title": task["title"],
        "repo_url": task["repo_url"],
        "base_commit": task["base_commit"],
        "fixed_commit": task["fixed_commit"],
        "base_setup": base_setup,
        "base_acceptance": asdict(base_acceptance),
        "fixed_setup": fixed_setup,
        "fixed_acceptance": asdict(fixed_acceptance),
        "ok": (not base_acceptance.ok) and fixed_acceptance.ok,
    }
    write_json(output_dir / "oracle.json", report)
    write_task_check_summary(output_dir / "summary.md", task, base_setup, base_acceptance, fixed_setup, fixed_acceptance)
    return 0 if report["ok"] else 1
