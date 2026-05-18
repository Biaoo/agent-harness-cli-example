from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from research_paths import resolve_config_path


def fail_result(
    *,
    name: str,
    severity: str,
    summary: str,
    reasons: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": name,
        "passed": False,
        "severity": severity,
        "summary": summary,
        "score": 0.0,
        "reasons": reasons,
        "metadata": metadata or {},
    }


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_csv_contract")
    severity = check.get("severity", "error")
    raw_path = str(config.get("path", ""))
    required_columns = [str(item) for item in config.get("required_columns", [])]
    nonempty_columns = [str(item) for item in config.get("nonempty_columns", required_columns)]
    min_rows = int(config.get("min_rows", 1))
    allowed_values = {
        str(column): [str(item) for item in values]
        for column, values in dict(config.get("allowed_values", {})).items()
    }

    if not raw_path:
        return fail_result(
            name=name,
            severity=severity,
            summary="CSV path is not configured.",
            reasons=[{
                "message": "check.config.path is required.",
                "suggestion": "Set check.config.path to the CSV artifact.",
                "requires_user_input": False,
            }],
        )

    display_path, path, context = resolve_config_path(root, raw_path, config)
    if not path.exists():
        return fail_result(
            name=name,
            severity=severity,
            summary="CSV artifact is missing.",
            reasons=[{
                "file": display_path,
                "message": "The required CSV artifact does not exist.",
                "suggestion": "Create the CSV with the configured columns.",
                "requires_user_input": False,
            }],
            metadata={"path": display_path, "raw_path": raw_path, "missing": True, "context": context},
        )

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            columns = reader.fieldnames or []
    except csv.Error as exc:
        return fail_result(
            name=name,
            severity=severity,
            summary="CSV artifact cannot be parsed.",
            reasons=[{
                "file": display_path,
                "message": f"CSV parse error: {exc}",
                "suggestion": "Rewrite the artifact as valid comma-separated CSV with a header row.",
                "requires_user_input": False,
            }],
            metadata={"path": display_path, "raw_path": raw_path, "context": context},
        )

    reasons: list[dict[str, Any]] = []
    missing_columns = [column for column in required_columns if column not in columns]
    for column in missing_columns:
        reasons.append({
            "file": display_path,
            "message": f"Missing required column: {column}",
            "suggestion": f"Add the `{column}` column to the CSV header.",
            "requires_user_input": False,
        })

    if len(rows) < min_rows:
        reasons.append({
            "file": display_path,
            "message": f"CSV has {len(rows)} data row(s), below the required minimum {min_rows}.",
            "suggestion": "Add enough substantive rows to support the current research stage.",
            "requires_user_input": False,
            "evidence": {"actual_rows": len(rows), "min_rows": min_rows},
        })

    for index, row in enumerate(rows, start=2):
        for column in nonempty_columns:
            if column in columns and not str(row.get(column, "")).strip():
                reasons.append({
                    "file": display_path,
                    "message": f"Row {index} has an empty `{column}` value.",
                    "suggestion": f"Fill `{column}` with a concrete value.",
                    "requires_user_input": False,
                })
        for column, values in allowed_values.items():
            if column in columns:
                value = str(row.get(column, "")).strip()
                if value and value not in values:
                    reasons.append({
                        "file": display_path,
                        "message": f"Row {index} has unsupported `{column}` value `{value}`.",
                        "suggestion": f"Use one of: {', '.join(values)}.",
                        "requires_user_input": False,
                    })

    passed = not reasons
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"CSV contract passed with {len(rows)} data row(s)."
            if passed
            else f"CSV contract has {len(reasons)} issue(s)."
        ),
        "score": 1.0 if passed else max(0.0, 1.0 - min(len(reasons), 10) / 10),
        "reasons": reasons,
        "metadata": {
            "path": display_path,
            "raw_path": raw_path,
            "context": context,
            "columns": columns,
            "row_count": len(rows),
            "required_columns": required_columns,
            "nonempty_columns": nonempty_columns,
            "allowed_values": allowed_values,
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
