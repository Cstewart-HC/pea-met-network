#!/usr/bin/env python3
"""
sync_state.py — Ralph loop state synchronizer.

Runs at the START of every loop iteration. Derives ground truth from
git history and the JSON state file, then updates ralph-state.json.

Gates are defined in ralph-state.json — machine-readable, no markdown parsing.

Usage:
    python scripts/sync_state.py [--check-only | --run-gates | --write]

    (no flags)      Print derived state, check gates, write JSON.
    --check-only    Print state without writing. Exit 1 if drift.
    --run-gates     Run all pending task gates, report results.
    --write         Write JSON only (for pre-commit hook).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "docs" / "ralph-state.json"


def git(*args: str) -> str:
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"git error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def git_log(n: int = 20) -> list[str]:
    """Get recent commit messages."""
    output = git("log", "--oneline", f"-{n}")
    return output.splitlines() if output else []


def derive_phase_from_commits(commits: list[str]) -> tuple[int, str]:
    """Derive the current phase from commit message prefixes."""
    phase_keywords = {
        1: {"audit", "data", "scaffold", "chore"},
        2: {"scrub", "clean", "normali", "resamp", "imput"},
        3: {"explore", "visual", "inspect"},
        4: {"model", "stanhope", "fwi", "moisture", "ref"},
        5: {"redund", "pca", "cluster", "benchmark"},
        6: {"interp", "uncertain", "recommend", "report"},
    }
    phase_names = {
        1: "Obtain",
        2: "Scrub",
        3: "Explore",
        4: "Model: Reference + FWI",
        5: "Model: Redundancy",
        6: "Interpret",
    }

    latest_phase = 1
    for line in commits:
        scope = line.split(":", 1)[-1].lower() if ":" in line else line.lower()
        for phase, keywords in phase_keywords.items():
            if any(kw in scope for kw in keywords):
                latest_phase = max(latest_phase, phase)

    return latest_phase, phase_names[latest_phase]


def run_gate(gate_cmd: str | None) -> tuple[bool, str]:
    """Run a verification gate command. Returns (passed, output)."""
    if not gate_cmd:
        return False, "no gate defined"
    try:
        result = subprocess.run(
            gate_cmd,
            shell=True,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout.strip()[:200]
        if result.returncode != 0 and result.stderr.strip():
            output = result.stderr.strip()[:200]
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "gate timed out (60s)"
    except Exception as e:
        return False, str(e)[:200]


def load_state() -> dict:
    """Load current ralph-state.json."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    """Write ralph-state.json atomically."""
    state["updated_at"] = datetime.now(
        timezone.utc
    ).astimezone().isoformat()
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    tmp.replace(STATE_FILE)


def get_next_task(state: dict) -> dict | None:
    """Find the first pending task whose dependencies are all done."""
    done_ids = {
        t["id"]
        for t in state.get("tasks", [])
        if t.get("status") == "done"
    }
    for task in state.get("tasks", []):
        if task.get("status") != "pending":
            continue
        deps = task.get("depends", [])
        if all(d in done_ids for d in deps):
            return task
    return None


def main() -> None:
    args = set(sys.argv[1:])
    check_only = "--check-only" in args
    run_gates_only = "--run-gates" in args
    write_only = "--write" in args

    # --- Derive ground truth from git ---
    commits = git_log()
    if not commits:
        print("No commits found", file=sys.stderr)
        sys.exit(1)

    latest_sha_short = commits[0].split()[0]
    phase, phase_name = derive_phase_from_commits(commits)

    # --- Load existing state ---
    state = load_state()

    if write_only:
        # Pre-commit hook: just re-derive phase and save
        state["phase"] = phase
        state["phase_name"] = phase_name
        save_state(state)
        return

    # --- Detect drift ---
    drift = []
    if state.get("phase") != phase:
        drift.append(f"phase: stored={state.get('phase')}, derived={phase}")
    if state.get("phase_name") != phase_name:
        drift.append(f"phase_name: stored={state.get('phase_name')}, derived={phase_name}")

    if check_only:
        if drift:
            print("DRIFT DETECTED:")
            for d in drift:
                print(f"  - {d}")
            sys.exit(1)
        else:
            print("State is in sync.")
            print(f"  Phase: {phase} — {phase_name}")
            print(f"  Commit: {latest_sha_short}")
            sys.exit(0)

    # --- Update phase from git ---
    state["phase"] = phase
    state["phase_name"] = phase_name

    # --- Find next task ---
    next_task = get_next_task(state)

    # --- Run gates mode ---
    if run_gates_only:
        print(f"COMMIT={latest_sha_short}")
        print(f"PHASE={phase}")
        print(f"PHASE_NAME={phase_name}")
        print()
        for task in state.get("tasks", []):
            status = task.get("status", "?")
            gate_cmd = task.get("gate", "")
            gate_ok, gate_out = run_gate(gate_cmd)
            actual = "PASS" if gate_ok else "FAIL"
            if status == "done" and not gate_ok:
                print(f"  DRIFT: {task['id']} marked done but gate FAILS")
                print(f"    gate: {gate_cmd}")
                print(f"    output: {gate_out}")
            elif status == "pending" and gate_ok:
                print(f"  UNMARKED: {task['id']} marked pending but gate PASSES")
                print(f"    gate: {gate_cmd}")
            else:
                print(f"  OK: {task['id']} [{status}] gate={actual}")
        return

    # --- Normal sync: check next task's gate ---
    done_count = sum(
        1 for t in state.get("tasks", []) if t.get("status") == "done"
    )
    pending_count = sum(
        1 for t in state.get("tasks", []) if t.get("status") == "pending"
    )

    save_state(state)

    # --- Print summary for the loop to consume ---
    print(f"PHASE={phase}")
    print(f"PHASE_NAME={phase_name}")
    print(f"COMMIT={latest_sha_short}")
    print(f"TASKS_DONE={done_count}")
    print(f"TASKS_LEFT={pending_count}")

    if drift:
        print("DRIFT_CORRECTED:")
        for d in drift:
            print(f"  {d}")

    if next_task:
        print(f"NEXT_TASK={next_task['id']}")
        print(f"NEXT_TASK_DESC={next_task['description']}")
        gate_cmd = next_task.get("gate", "")
        print(f"GATE_CMD={gate_cmd}")
        if gate_cmd:
            gate_ok, gate_out = run_gate(gate_cmd)
            if gate_ok:
                print("GATE_STATUS=ALREADY_PASSES")
            else:
                print("GATE_STATUS=NOT_YET")
                if gate_out:
                    print(f"GATE_OUTPUT={gate_out}")
        deps = next_task.get("depends", [])
        if deps:
            print(f"DEPENDS={','.join(deps)}")
    else:
        print("NEXT_TASK=NONE")
        if pending_count == 0:
            print("ALL_TASKS_COMPLETE=true")


if __name__ == "__main__":
    main()
