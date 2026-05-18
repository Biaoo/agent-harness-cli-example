from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_RE = re.compile(r"^\s*(?:status|状态)\s*[:：]\s*(?P<status>[A-Za-z0-9_/-]+)\s*$", re.IGNORECASE)


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def extract_status(text: str) -> str | None:
    for line in text.splitlines():
        match = STATUS_RE.match(line)
        if match:
            return match.group("status").strip()
    return None


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_status")
    severity = check.get("severity", "error")
    raw_path = str(config.get("path", ""))
    allowed_statuses = [str(item) for item in config.get("allowed_statuses", [])]

    if not raw_path:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Research status artifact path is not configured.",
            "score": 0.0,
            "reasons": [{
                "message": "check.config.path is required.",
                "suggestion": "Set check.config.path to the Markdown artifact that contains a Status line.",
                "requires_user_input": False
            }]
        }

    path = resolve(root, raw_path)
    if not path.exists():
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Research status artifact is missing.",
            "score": 0.0,
            "reasons": [{
                "file": raw_path,
                "message": "The artifact does not exist, so no routing status can be read.",
                "suggestion": "Create the artifact and add a line like `Status: clarified`.",
                "requires_user_input": False
            }],
            "metadata": {"path": raw_path, "status": ""}
        }

    text = path.read_text(encoding="utf-8")
    status = extract_status(text)
    if status is None:
        return {
            "check": name,
            "passed": False,
            "severity": severity,
            "summary": "Research routing status is missing.",
            "score": 0.0,
            "reasons": [{
                "file": raw_path,
                "message": "No `Status: <value>` line was found.",
                "suggestion": f"Add one allowed status: {', '.join(allowed_statuses)}.",
                "requires_user_input": False
            }],
            "metadata": {"path": raw_path, "status": ""}
        }

    passed = not allowed_statuses or status in allowed_statuses
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"Research routing status is `{status}`."
            if passed
            else f"Research routing status `{status}` is not allowed for this node."
        ),
        "score": 1.0 if passed else 0.0,
        "reasons": [] if passed else [{
            "file": raw_path,
            "message": f"Status `{status}` is not in the allowed set for this workflow node.",
            "suggestion": f"Use one of: {', '.join(allowed_statuses)}.",
            "requires_user_input": False,
            "evidence": {"status": status, "allowed_statuses": allowed_statuses}
        }],
        "metadata": {
            "path": raw_path,
            "status": status,
            "allowed_statuses": allowed_statuses
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
