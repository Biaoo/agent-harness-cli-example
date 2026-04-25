from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def artifact_path(task: dict[str, Any], artifact_name: str) -> str | None:
    for artifact in task.get("artifacts", []):
        if artifact.get("name") == artifact_name:
            return artifact.get("path")
    return None


def count_non_whitespace(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    task = input_data["task"]
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "essay_length")
    severity = check.get("severity", "error")
    artifact_name = config.get("artifact", "essay")
    target = int(config.get("target_chars", 1000))
    tolerance = int(config.get("tolerance", 10))
    raw_path = artifact_path(task, artifact_name)

    if raw_path is None:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Configured artifact was not found.",
            "score": 0.0,
            "reasons": [
                {
                    "message": f"Task has no artifact named {artifact_name}.",
                    "suggestion": "Add the artifact to task.artifacts or update check.config.artifact.",
                    "requires_user_input": False
                }
            ]
        }

    path = resolve(root, raw_path)
    if not path.exists():
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Essay file does not exist.",
            "score": 0.0,
            "reasons": [
                {
                    "file": raw_path,
                    "message": "Essay artifact is missing.",
                    "suggestion": "Create the essay file or correct the artifact path.",
                    "requires_user_input": False
                }
            ]
        }

    text = path.read_text(encoding="utf-8")
    actual = count_non_whitespace(text)
    minimum = target - tolerance
    maximum = target + tolerance
    passed = minimum <= actual <= maximum
    delta = abs(actual - target)

    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"Essay length is {actual} characters, within {minimum}-{maximum}."
            if passed
            else f"Essay length is {actual} characters, outside {minimum}-{maximum}."
        ),
        "score": 1.0 if passed else max(0.0, 1.0 - delta / target),
        "reasons": [] if passed else [
            {
                "file": raw_path,
                "message": f"Expected {target} +/- {tolerance} non-whitespace characters, got {actual}.",
                "suggestion": "Add or remove content until the non-whitespace character count is between the allowed bounds.",
                "requires_user_input": False,
                "evidence": {
                    "actual_chars": actual,
                    "target_chars": target,
                    "tolerance": tolerance,
                    "count_mode": "non_whitespace"
                }
            }
        ],
        "metadata": {
            "actual_chars": actual,
            "target_chars": target,
            "tolerance": tolerance,
            "count_mode": "non_whitespace"
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
