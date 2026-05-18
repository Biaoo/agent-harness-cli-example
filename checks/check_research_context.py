from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from research_paths import resolve


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


def result(
    *,
    name: str,
    severity: str,
    passed: bool,
    summary: str,
    reasons: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": summary,
        "score": 1.0 if passed else 0.0,
        "reasons": reasons,
        "metadata": metadata or {},
    }


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_context")
    severity = check.get("severity", "error")
    raw_path = str(config.get("path", "research/context.json"))
    path = resolve(root, raw_path)

    if not path.exists():
        return result(
            name=name,
            severity=severity,
            passed=False,
            summary="Research context is missing.",
            reasons=[{
                "file": raw_path,
                "message": "The workflow needs a topic context before it can resolve artifact paths.",
                "suggestion": "Create research/context.json with topic_title, topic_slug, and research_dir.",
                "requires_user_input": False,
            }],
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return result(
            name=name,
            severity=severity,
            passed=False,
            summary="Research context is not valid JSON.",
            reasons=[{
                "file": raw_path,
                "message": f"JSON parse error: {exc}",
                "suggestion": "Rewrite research/context.json as a valid JSON object.",
                "requires_user_input": False,
            }],
        )

    reasons: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        reasons.append({
            "file": raw_path,
            "message": "Research context must be a JSON object.",
            "suggestion": "Use an object with topic_title, topic_slug, and research_dir.",
            "requires_user_input": False,
        })
        data = {}

    topic_title = str(data.get("topic_title", "")).strip()
    topic_slug = str(data.get("topic_slug", "")).strip()
    research_dir = str(data.get("research_dir", "")).strip() or f"research/{topic_slug}"
    expected_dir = f"research/{topic_slug}" if topic_slug else ""

    if not topic_title:
        reasons.append({
            "file": raw_path,
            "message": "`topic_title` is missing.",
            "suggestion": "Set topic_title to a concise human-readable research topic.",
            "requires_user_input": False,
        })

    if not topic_slug or not SLUG_RE.fullmatch(topic_slug):
        reasons.append({
            "file": raw_path,
            "message": "`topic_slug` must be a lower-kebab ASCII slug.",
            "suggestion": "Use 3-64 characters: lowercase letters, numbers, and single hyphens.",
            "requires_user_input": False,
            "evidence": {"topic_slug": topic_slug},
        })

    if topic_slug and research_dir != expected_dir:
        reasons.append({
            "file": raw_path,
            "message": "`research_dir` must match the topic slug.",
            "suggestion": f"Set research_dir to `{expected_dir}`.",
            "requires_user_input": False,
            "evidence": {"research_dir": research_dir, "expected": expected_dir},
        })

    if research_dir:
        resolved_dir = resolve(root, research_dir)
        if not resolved_dir.exists() or not resolved_dir.is_dir():
            reasons.append({
                "file": raw_path,
                "message": "The topic research directory does not exist.",
                "suggestion": f"Create `{research_dir}/` before advancing.",
                "requires_user_input": False,
            })

    metadata = {
        "path": raw_path,
        "topic_title": topic_title,
        "topic_slug": topic_slug,
        "research_dir": research_dir,
    }
    return result(
        name=name,
        severity=severity,
        passed=not reasons,
        summary=(
            f"Research context points to `{research_dir}`."
            if not reasons
            else "Research context is incomplete or invalid."
        ),
        reasons=reasons,
        metadata=metadata,
    )


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
