from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from local_codex_judge import run_codex_checklist_judge


CHECKBOX_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<text>.+)$")
STATUS_RE = re.compile(r"^\s*(?:status|状态)\s*[:：]\s*(?P<status>[A-Za-z0-9_/-]+)\s*$", re.IGNORECASE)


def field_value(line: str) -> str:
    return line.split(":", 1)[1].strip() if ":" in line else ""


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def extract_status(text: str) -> str:
    for line in text.splitlines():
        match = STATUS_RE.match(line)
        if match:
            return match.group("status").strip()
    return ""


def skipped_result(name: str, severity: str, aspect: str) -> dict[str, Any]:
    return {
        "check": name,
        "passed": True,
        "severity": severity,
        "summary": "Research checklist check skipped because AGENT_HARNESS_ENABLE_LLM=0.",
        "score": 1.0,
        "reasons": [],
        "metadata": {
            "skipped": True,
            "aspect": aspect,
            "enable_with": "unset AGENT_HARNESS_ENABLE_LLM or set it to 1",
        },
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


def missing_file_result(name: str, severity: str, raw_path: str, message: str, suggestion: str) -> dict[str, Any]:
    return {
        "check": name,
        "passed": False,
        "severity": severity,
        "summary": message,
        "score": 0.0,
        "reasons": [{
            "file": raw_path,
            "message": message,
            "suggestion": suggestion,
            "requires_user_input": False,
        }],
    }


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    node = input_data.get("node", {})
    config = check.get("config", {})
    name = check.get("name", "research_checklist")
    severity = check.get("severity", "error")
    aspect = str(config.get("aspect", name))

    if os.environ.get("AGENT_HARNESS_ENABLE_LLM") == "0":
        return skipped_result(name, severity, aspect)

    raw_path = str(config.get("path", ""))
    checklist_ref = str(config.get("checklist", ""))
    if not raw_path:
        return missing_file_result(
            name,
            severity,
            "",
            "Research artifact path is not configured.",
            "Set check.config.path to the active research artifact.",
        )
    if not checklist_ref:
        return missing_file_result(
            name,
            severity,
            raw_path,
            "Research checklist path is not configured.",
            "Set check.config.checklist to a Markdown checklist template.",
        )

    artifact_path = resolve(root, raw_path)
    if not artifact_path.exists():
        return missing_file_result(
            name,
            severity,
            raw_path,
            "Research artifact is missing.",
            "Create the artifact before running the content checklist.",
        )

    checklist_path = resolve(root, checklist_ref)
    if not checklist_path.exists():
        return missing_file_result(
            name,
            severity,
            checklist_ref,
            "Research checklist template is missing.",
            "Create the configured checklist template.",
        )

    artifact = artifact_path.read_text(encoding="utf-8")
    status = extract_status(artifact)
    checklist_template = checklist_path.read_text(encoding="utf-8")
    node_id = node.get("id", "unknown_node") if isinstance(node, dict) else "unknown_node"
    node_title = node.get("title", node_id) if isinstance(node, dict) else node_id

    prompt = f"""
You are a strict research quality reviewer for an Agent Harness workflow.
Evaluate only the artifact against the checklist criteria.
Do not reward fluent prose, generic plausibility, or optimistic status labels.
Mark an item as satisfied only when the artifact provides concrete evidence.

Workflow node: {node_id} ({node_title})
Checklist aspect: {aspect}
Artifact path: {raw_path}
Artifact status: {status or "<missing>"}

Research rule:
Either the work supports a main-text-level insight, or it must route back for repair.
Do not accept SI-only digestion, downgrade publication, or fallback-paper framing.

Artifact:
{artifact}
""".strip()

    try:
        filled = run_codex_checklist_judge(
            prompt=prompt,
            checklist_template=checklist_template,
            working_directory=root,
            model=config.get("model"),
            reasoning_effort=str(config.get("reasoning_effort", "medium")),
            timeout_seconds=float(config.get("timeout_seconds", 240.0)),
        )
    except Exception as exc:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Local Codex research checklist judge failed.",
            "score": 0.0,
            "reasons": [{
                "message": f"{type(exc).__name__}: {exc}",
                "suggestion": "Verify local Codex CLI authentication/runtime, or set AGENT_HARNESS_ENABLE_LLM=0 for deterministic-only debugging.",
                "requires_user_input": True,
                "evidence": {"aspect": aspect, "checklist": checklist_ref},
            }],
            "metadata": {"aspect": aspect, "provider": "local-codex-checklist"},
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
                "suggestion": "Tighten the checklist template or inspect the raw checklist output.",
                "requires_user_input": False,
                "evidence": {"raw_output": filled[:1000], "checklist": checklist_ref},
            }],
            "metadata": {"aspect": aspect, "provider": "local-codex-checklist"},
        }

    failed_items = [item for item in items if not item["checked"]]
    passed = not failed_items
    score = (len(items) - len(failed_items)) / len(items)
    reasons = [
        {
            "file": raw_path,
            "message": item["criterion"] or item["text"],
            "suggestion": item["suggestion"] or "Revise the artifact so this checklist item is satisfied.",
            "requires_user_input": False,
            "evidence": {
                "aspect": aspect,
                "item_id": item["item_id"],
                "reason": item["reason"],
                "judge_evidence": item["evidence_text"],
                "checklist": checklist_ref,
                "status": status,
            },
        }
        for item in failed_items
    ]

    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"All {len(items)} research checklist item(s) are satisfied."
            if passed
            else f"{len(failed_items)}/{len(items)} research checklist item(s) are not satisfied."
        ),
        "score": score,
        "reasons": reasons,
        "metadata": {
            "aspect": aspect,
            "provider": "local-codex-checklist",
            "checklist": checklist_ref,
            "status": status,
            "filled_checklist": filled,
        },
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
