from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from research_paths import resolve_config_path


SPLIT_RE = re.compile(r"[;,]")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def split_ids(value: str) -> list[str]:
    return [part.strip() for part in SPLIT_RE.split(value or "") if part.strip()]


def fail_result(name: str, severity: str, reasons: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "check": name,
        "passed": False,
        "severity": severity,
        "summary": f"Research trace links have {len(reasons)} issue(s).",
        "score": 0.0,
        "reasons": reasons,
        "metadata": metadata,
    }


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_trace_links")
    severity = check.get("severity", "error")
    trace_ref = str(config.get("claim_trace", "research/{topic_slug}/claim_evidence_trace.csv"))
    source_ref = str(config.get("source_pack", "research/{topic_slug}/source_evidence_pack.csv"))
    data_fitness_ref = str(config.get("data_fitness", ""))

    trace_display, trace_path, context = resolve_config_path(root, trace_ref, config)
    source_display, source_path, _ = resolve_config_path(root, source_ref, config)
    reasons: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {
        "claim_trace": trace_display,
        "source_pack": source_display,
        "context": context,
    }

    if not trace_path.exists():
        reasons.append({
            "file": trace_display,
            "message": "Claim-evidence trace is missing.",
            "suggestion": "Create claim_evidence_trace.csv before this gate.",
            "requires_user_input": False,
        })
    if not source_path.exists():
        reasons.append({
            "file": source_display,
            "message": "Source evidence pack is missing.",
            "suggestion": "Create source_evidence_pack.csv before this gate.",
            "requires_user_input": False,
        })
    if reasons:
        return fail_result(name, severity, reasons, metadata)

    trace_columns, trace_rows = read_csv(trace_path)
    source_columns, source_rows = read_csv(source_path)
    metadata["trace_rows"] = len(trace_rows)
    metadata["source_rows"] = len(source_rows)

    if "claim_id" not in trace_columns or "source_ids" not in trace_columns:
        reasons.append({
            "file": trace_display,
            "message": "Claim trace must contain `claim_id` and `source_ids` columns.",
            "suggestion": "Add both columns and populate source_ids with source IDs from the evidence pack.",
            "requires_user_input": False,
        })
    if "source_id" not in source_columns:
        reasons.append({
            "file": source_display,
            "message": "Source evidence pack must contain a `source_id` column.",
            "suggestion": "Add source_id values such as S1, S2, or E1.",
            "requires_user_input": False,
        })
    if reasons:
        return fail_result(name, severity, reasons, metadata)

    source_ids = {row.get("source_id", "").strip() for row in source_rows if row.get("source_id", "").strip()}
    claim_ids = {row.get("claim_id", "").strip() for row in trace_rows if row.get("claim_id", "").strip()}
    metadata["source_ids"] = sorted(source_ids)
    metadata["claim_ids"] = sorted(claim_ids)

    for index, row in enumerate(trace_rows, start=2):
        claim_id = row.get("claim_id", "").strip() or f"row {index}"
        row_source_ids = split_ids(row.get("source_ids", ""))
        if not row_source_ids:
            reasons.append({
                "file": trace_display,
                "message": f"Claim `{claim_id}` has no source_ids.",
                "suggestion": "Link every claim to at least one source_id from source_evidence_pack.csv.",
                "requires_user_input": False,
            })
        for source_id in row_source_ids:
            if source_id not in source_ids:
                reasons.append({
                    "file": trace_display,
                    "message": f"Claim `{claim_id}` references unknown source_id `{source_id}`.",
                    "suggestion": "Add the source to source_evidence_pack.csv or correct the source_ids value.",
                    "requires_user_input": False,
                })

    if data_fitness_ref:
        data_display, data_path, _ = resolve_config_path(root, data_fitness_ref, config)
        metadata["data_fitness"] = data_display
        if not data_path.exists():
            reasons.append({
                "file": data_display,
                "message": "Data fitness matrix is missing.",
                "suggestion": "Create data_fitness_matrix.csv before this gate.",
                "requires_user_input": False,
            })
        else:
            data_columns, data_rows = read_csv(data_path)
            metadata["data_fitness_rows"] = len(data_rows)
            if "claim_id" not in data_columns:
                reasons.append({
                    "file": data_display,
                    "message": "Data fitness matrix must contain a `claim_id` column.",
                    "suggestion": "Add claim_id values matching claim_evidence_trace.csv.",
                    "requires_user_input": False,
                })
            else:
                for index, row in enumerate(data_rows, start=2):
                    claim_id = row.get("claim_id", "").strip()
                    if claim_id and claim_id not in claim_ids:
                        reasons.append({
                            "file": data_display,
                            "message": f"Row {index} references unknown claim_id `{claim_id}`.",
                            "suggestion": "Use a claim_id from claim_evidence_trace.csv or add the missing claim.",
                            "requires_user_input": False,
                        })

    passed = not reasons
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            "Research trace links are internally consistent."
            if passed
            else f"Research trace links have {len(reasons)} issue(s)."
        ),
        "score": 1.0 if passed else max(0.0, 1.0 - min(len(reasons), 10) / 10),
        "reasons": reasons,
        "metadata": metadata,
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
