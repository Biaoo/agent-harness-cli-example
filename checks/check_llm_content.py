from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from local_codex_judge import run_codex_checklist_judge


CHECKBOX_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<text>.+)$")


def field_value(line: str) -> str:
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def artifact_path(task: dict[str, Any], artifact_name: str) -> str | None:
    for artifact in task.get("artifacts", []):
        if artifact.get("name") == artifact_name:
            return artifact.get("path")
    return None


def skipped_result(name: str, severity: str, aspect: str) -> dict[str, Any]:
    return {
        "check": name,
        "passed": True,
        "severity": severity,
        "summary": "LLM checklist check skipped because AGENT_HARNESS_ENABLE_LLM is not set to 1.",
        "score": 1.0,
        "reasons": [],
        "metadata": {
            "skipped": True,
            "aspect": aspect,
            "enable_with": "AGENT_HARNESS_ENABLE_LLM=1"
        }
    }


def parse_checklist(markdown: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        match = CHECKBOX_RE.match(line)
        if match:
            text = match.group("text").strip()
            item_id = text.split(":", 1)[1].strip() if text.startswith("item_id:") else ""
            current = {
                "checked": match.group("mark").lower() == "x",
                "text": text,
                "item_id": item_id,
                "criterion": "",
                "evidence_text": "",
                "reason": "",
                "suggestion": "",
            }
            items.append(current)
            continue
        if current is None:
            continue
        lower = line.lower()
        if lower.startswith("criterion:"):
            current["criterion"] = field_value(line)
        elif lower.startswith("evidence:"):
            current["evidence_text"] = field_value(line)
        elif lower.startswith("reason:"):
            current["reason"] = field_value(line)
        elif lower.startswith("suggestion:"):
            current["suggestion"] = field_value(line)
    return items


def missing_artifact_result(name: str, severity: str, raw_path: str, aspect: str) -> dict[str, Any]:
    return {
        "check": name,
        "passed": False,
        "severity": severity,
        "summary": "Essay artifact is missing.",
        "score": 0.0,
        "reasons": [{
            "file": raw_path,
            "message": "The essay file does not exist, so Codex cannot judge its content.",
            "suggestion": "Ask Codex to write the essay to essay.md, then rerun the harness.",
            "requires_user_input": False,
            "evidence": {"aspect": aspect}
        }],
        "metadata": {"aspect": aspect, "provider": "local-codex-checklist"}
    }


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    task = input_data["task"]
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "llm_content")
    severity = check.get("severity", "warning")
    aspect = config.get("aspect", name)

    if os.environ.get("AGENT_HARNESS_ENABLE_LLM") != "1":
        return skipped_result(name, severity, aspect)

    artifact_name = config.get("artifact", "essay")
    raw_path = artifact_path(task, artifact_name)
    if raw_path is None:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Configured artifact was not found.",
            "score": 0.0,
            "reasons": [{
                "message": f"Task has no artifact named {artifact_name}.",
                "suggestion": "Add the artifact to task.artifacts or update check.config.artifact.",
                "requires_user_input": False
            }]
        }

    essay_path = resolve(root, raw_path)
    if not essay_path.exists():
        return missing_artifact_result(name, severity, raw_path, aspect)

    checklist_ref = config.get("checklist")
    if not checklist_ref:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "LLM checklist path is missing.",
            "score": 0.0,
            "reasons": [{
                "message": "check.config.checklist is required for checklist-based LLM checks.",
                "suggestion": "Add a markdown checklist file and point check.config.checklist to it.",
                "requires_user_input": False
            }]
        }

    essay = essay_path.read_text(encoding="utf-8")
    checklist_template = resolve(root, checklist_ref).read_text(encoding="utf-8")
    prompt = f"""
You are a strict but restrained essay reviewer. Evaluate the essay only against the criteria written in the checklist.
Do not introduce content requirements beyond the checklist.
If an item is not satisfied, keep that item unchecked and add a brief Reason and Suggestion.

Essay:
{essay}
""".strip()

    try:
        filled = run_codex_checklist_judge(
            prompt=prompt,
            checklist_template=checklist_template,
            working_directory=root,
            model=config.get("model"),
            reasoning_effort=config.get("reasoning_effort", "low"),
        )
    except Exception as exc:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Local Codex checklist judge failed.",
            "score": 0.0,
            "reasons": [{
                "message": f"{type(exc).__name__}: {exc}",
                "suggestion": "Verify local Codex CLI authentication/runtime, or run without AGENT_HARNESS_ENABLE_LLM=1.",
                "requires_user_input": True,
                "evidence": {"aspect": aspect}
            }],
            "metadata": {"aspect": aspect, "provider": "local-codex-checklist"}
        }

    items = parse_checklist(filled)
    if not items:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Codex returned no parseable checklist items.",
            "score": 0.0,
            "reasons": [{
                "message": "No markdown checklist items were found in Codex output.",
                "suggestion": "Tighten the checklist prompt or inspect the raw checklist output.",
                "requires_user_input": False,
                "evidence": {"raw_output": filled[:1000]}
            }],
            "metadata": {"aspect": aspect, "provider": "local-codex-checklist"}
        }

    failed_items = [item for item in items if not item["checked"]]
    passed = not failed_items
    score = (len(items) - len(failed_items)) / len(items)
    reasons = [
        {
            "file": raw_path,
            "message": item["criterion"] or item["text"],
            "suggestion": item["suggestion"] or "Revise the essay so this checklist item is satisfied.",
            "requires_user_input": False,
            "evidence": {
                "aspect": aspect,
                "item_id": item["item_id"],
                "reason": item["reason"],
                "judge_evidence": item["evidence_text"],
                "checklist": checklist_ref
            }
        }
        for item in failed_items
    ]

    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"All {len(items)} checklist item(s) are satisfied."
            if passed
            else f"{len(failed_items)}/{len(items)} checklist item(s) are not satisfied."
        ),
        "score": score,
        "reasons": reasons,
        "metadata": {
            "aspect": aspect,
            "provider": "local-codex-checklist",
            "checklist": checklist_ref,
            "filled_checklist": filled
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    with open(args.input, "r", encoding="utf-8") as handle:
        input_data = json.load(handle)
    print(json.dumps(run(input_data), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
