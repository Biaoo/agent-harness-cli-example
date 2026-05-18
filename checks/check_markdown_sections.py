from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "markdown_sections")
    severity = check.get("severity", "error")
    raw_path = str(config.get("path", ""))
    required_headings = [str(item) for item in config.get("required_headings", [])]
    min_chars = int(config.get("min_chars", 0))

    if not raw_path:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Markdown artifact path is not configured.",
            "score": 0.0,
            "reasons": [{
                "message": "check.config.path is required.",
                "suggestion": "Set check.config.path to the Markdown artifact path.",
                "requires_user_input": False
            }]
        }

    path = resolve(root, raw_path)
    if not path.exists():
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Markdown artifact is missing.",
            "score": 0.0,
            "reasons": [{
                "file": raw_path,
                "message": "The required Markdown artifact does not exist.",
                "suggestion": "Create this artifact and include the required headings.",
                "requires_user_input": False
            }],
            "metadata": {"path": raw_path, "missing": True}
        }

    text = path.read_text(encoding="utf-8")
    lines = {line.strip() for line in text.splitlines()}
    missing_headings = [heading for heading in required_headings if heading not in lines]
    too_short = min_chars > 0 and len(text.strip()) < min_chars
    reasons: list[dict[str, Any]] = []

    for heading in missing_headings:
        reasons.append({
            "file": raw_path,
            "message": f"Missing required heading: {heading}",
            "suggestion": f"Add a `{heading}` section with concrete research content.",
            "requires_user_input": False
        })

    if too_short:
        reasons.append({
            "file": raw_path,
            "message": f"Artifact has {len(text.strip())} characters, below the required minimum {min_chars}.",
            "suggestion": "Expand the artifact with concrete claims, evidence, decisions, and open blockers.",
            "requires_user_input": False,
            "evidence": {"actual_chars": len(text.strip()), "min_chars": min_chars}
        })

    passed = not reasons
    total_requirements = len(required_headings) + (1 if min_chars > 0 else 0)
    failed_requirements = len(missing_headings) + (1 if too_short else 0)
    score = 1.0 if total_requirements == 0 else (total_requirements - failed_requirements) / total_requirements

    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"Markdown artifact contains all {len(required_headings)} required heading(s)."
            if passed
            else f"Markdown artifact is missing {len(missing_headings)} heading(s)"
                 f"{' and is too short' if too_short else ''}."
        ),
        "score": score,
        "reasons": reasons,
        "metadata": {
            "path": raw_path,
            "required_headings": required_headings,
            "missing_headings": missing_headings,
            "actual_chars": len(text.strip()),
            "min_chars": min_chars
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
