from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from research_paths import resolve_config_path


STATUS_RE = re.compile(r"^\s*Status:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)


REQUIRED_COLUMNS = [
    "dimension",
    "score",
    "threshold",
    "verdict",
    "rationale",
    "required_action",
    "route",
]


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


def parse_float(value: str) -> float | None:
    try:
        return float(value.strip())
    except ValueError:
        return None


def load_status(path: Path) -> str:
    match = STATUS_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else ""


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_review_scorecard")
    severity = check.get("severity", "error")
    scorecard_raw = str(config.get("scorecard", ""))
    report_raw = str(config.get("report", ""))
    min_rows = int(config.get("min_rows", 8))
    min_accept_mean = float(config.get("min_accept_mean", 4.2))
    min_accept_score = float(config.get("min_accept_score", 4.0))
    required_dimensions = [str(item) for item in config.get("required_dimensions", [
        "novelty",
        "literature_positioning",
        "evidence_adequacy",
        "method_validity",
        "analysis_quality",
        "claim_calibration",
        "figures_tables",
        "writing_structure",
        "reproducibility_references",
    ])]
    allowed_statuses = [str(item) for item in config.get("allowed_statuses", [
        "accept",
        "minor_revision",
        "major_revision",
        "needs_data",
        "reject_rewrite",
        "blocked",
    ])]
    allowed_verdicts = [str(item) for item in config.get("allowed_verdicts", [
        "pass",
        "minor_issue",
        "major_issue",
        "fatal_issue",
    ])]
    allowed_routes = [str(item) for item in config.get("allowed_routes", [
        "final_quality_review",
        "figures_manuscript",
        "results_architecture",
        "analysis",
        "data_acquisition",
        "research_design",
        "insight_direction_discovery",
        "idea_intake",
        "blocked",
    ])]

    if not scorecard_raw or not report_raw:
        return fail_result(
            name=name,
            severity=severity,
            summary="Review scorecard check is not fully configured.",
            reasons=[{
                "message": "check.config.scorecard and check.config.report are required.",
                "suggestion": "Set both paths in the workflow check config.",
                "requires_user_input": False,
            }],
        )

    scorecard_display, scorecard_path, context = resolve_config_path(root, scorecard_raw, config)
    report_display, report_path, _ = resolve_config_path(root, report_raw, config)
    if not scorecard_path.exists():
        return fail_result(
            name=name,
            severity=severity,
            summary="Review scorecard is missing.",
            reasons=[{
                "file": scorecard_display,
                "message": "The required reviewer_scorecard.csv artifact does not exist.",
                "suggestion": "Create a strict reviewer scorecard with one row per review dimension.",
                "requires_user_input": False,
            }],
            metadata={"scorecard": scorecard_display, "missing": True, "context": context},
        )
    if not report_path.exists():
        return fail_result(
            name=name,
            severity=severity,
            summary="Review report is missing.",
            reasons=[{
                "file": report_display,
                "message": "The required strict_paper_review.md artifact does not exist.",
                "suggestion": "Create the strict review report and include a Status line.",
                "requires_user_input": False,
            }],
            metadata={"report": report_display, "missing": True, "context": context},
        )

    try:
        with scorecard_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
            columns = reader.fieldnames or []
    except csv.Error as exc:
        return fail_result(
            name=name,
            severity=severity,
            summary="Review scorecard cannot be parsed.",
            reasons=[{
                "file": scorecard_display,
                "message": f"CSV parse error: {exc}",
                "suggestion": "Rewrite the scorecard as valid CSV with a header row.",
                "requires_user_input": False,
            }],
            metadata={"scorecard": scorecard_display, "context": context},
        )

    status = load_status(report_path)
    reasons: list[dict[str, Any]] = []
    if not status:
        reasons.append({
            "file": report_display,
            "message": "Review report is missing a `Status: <value>` line.",
            "suggestion": f"Use one of: {', '.join(allowed_statuses)}.",
            "requires_user_input": False,
        })
    elif status not in allowed_statuses:
        reasons.append({
            "file": report_display,
            "message": f"Review report status `{status}` is not allowed.",
            "suggestion": f"Use one of: {', '.join(allowed_statuses)}.",
            "requires_user_input": False,
        })

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
    for column in missing_columns:
        reasons.append({
            "file": scorecard_display,
            "message": f"Missing required column: {column}",
            "suggestion": f"Add the `{column}` column to reviewer_scorecard.csv.",
            "requires_user_input": False,
        })

    if len(rows) < min_rows:
        reasons.append({
            "file": scorecard_display,
            "message": f"Scorecard has {len(rows)} data row(s), below the required minimum {min_rows}.",
            "suggestion": "Score all required review dimensions instead of reviewing only a subset.",
            "requires_user_input": False,
            "evidence": {"actual_rows": len(rows), "min_rows": min_rows},
        })

    dimensions = {row.get("dimension", "") for row in rows}
    missing_dimensions = [dimension for dimension in required_dimensions if dimension not in dimensions]
    for dimension in missing_dimensions:
        reasons.append({
            "file": scorecard_display,
            "message": f"Missing required review dimension: {dimension}",
            "suggestion": "Score every required dimension; do not omit hard dimensions to make the paper pass.",
            "requires_user_input": False,
        })

    scores: list[float] = []
    failing_dimensions: list[str] = []
    fatal_dimensions: list[str] = []
    major_dimensions: list[str] = []
    routes: set[str] = set()

    for index, row in enumerate(rows, start=2):
        dimension = row.get("dimension", "")
        score_value = parse_float(row.get("score", ""))
        threshold_value = parse_float(row.get("threshold", ""))
        verdict = row.get("verdict", "")
        route = row.get("route", "")

        for column in REQUIRED_COLUMNS:
            if column in columns and not row.get(column):
                reasons.append({
                    "file": scorecard_display,
                    "message": f"Row {index} has an empty `{column}` value.",
                    "suggestion": f"Fill `{column}` with a concrete strict-review value.",
                    "requires_user_input": False,
                })

        if score_value is None:
            reasons.append({
                "file": scorecard_display,
                "message": f"Row {index} score is not numeric: `{row.get('score', '')}`.",
                "suggestion": "Use a numeric score from 1.0 to 5.0.",
                "requires_user_input": False,
            })
        elif not 1.0 <= score_value <= 5.0:
            reasons.append({
                "file": scorecard_display,
                "message": f"Row {index} score {score_value} is outside the allowed 1.0-5.0 range.",
                "suggestion": "Use the strict reviewer score scale from 1.0 to 5.0.",
                "requires_user_input": False,
            })
        else:
            scores.append(score_value)

        if threshold_value is None:
            reasons.append({
                "file": scorecard_display,
                "message": f"Row {index} threshold is not numeric: `{row.get('threshold', '')}`.",
                "suggestion": "Use a numeric threshold, usually 4.0 for completion-quality review.",
                "requires_user_input": False,
            })
        elif threshold_value < min_accept_score:
            reasons.append({
                "file": scorecard_display,
                "message": f"Row {index} threshold {threshold_value} is below the configured minimum {min_accept_score}.",
                "suggestion": "Do not lower the reviewer threshold to make the paper pass.",
                "requires_user_input": False,
            })

        if verdict and verdict not in allowed_verdicts:
            reasons.append({
                "file": scorecard_display,
                "message": f"Row {index} has unsupported verdict `{verdict}`.",
                "suggestion": f"Use one of: {', '.join(allowed_verdicts)}.",
                "requires_user_input": False,
            })
        if route and route not in allowed_routes:
            reasons.append({
                "file": scorecard_display,
                "message": f"Row {index} has unsupported route `{route}`.",
                "suggestion": f"Use one of: {', '.join(allowed_routes)}.",
                "requires_user_input": False,
            })

        if score_value is not None and threshold_value is not None and score_value < threshold_value:
            failing_dimensions.append(dimension or f"row_{index}")
        if verdict == "fatal_issue":
            fatal_dimensions.append(dimension or f"row_{index}")
        if verdict == "major_issue":
            major_dimensions.append(dimension or f"row_{index}")
        if route:
            routes.add(route)

    mean_score = sum(scores) / len(scores) if scores else 0.0

    if status == "accept":
        if mean_score < min_accept_mean:
            reasons.append({
                "file": scorecard_display,
                "message": f"Accept status is inconsistent with mean score {mean_score:.2f} below {min_accept_mean:.2f}.",
                "suggestion": "Route to revision instead of accepting, or substantially improve the manuscript and evidence.",
                "requires_user_input": False,
            })
        if failing_dimensions:
            reasons.append({
                "file": scorecard_display,
                "message": f"Accept status has below-threshold dimension(s): {', '.join(failing_dimensions)}.",
                "suggestion": "A paper cannot finish until every review dimension reaches its threshold.",
                "requires_user_input": False,
            })
        if fatal_dimensions or major_dimensions:
            reasons.append({
                "file": scorecard_display,
                "message": "Accept status is inconsistent with major or fatal reviewer issues.",
                "suggestion": "Use major_revision, needs_data, or reject_rewrite until major/fatal issues are resolved.",
                "requires_user_input": False,
                "evidence": {"major": major_dimensions, "fatal": fatal_dimensions},
            })

    if status == "minor_revision" and (major_dimensions or fatal_dimensions):
        reasons.append({
            "file": scorecard_display,
            "message": "`minor_revision` status is inconsistent with major or fatal reviewer issues.",
            "suggestion": "Use major_revision, needs_data, or reject_rewrite when the review identifies major/fatal flaws.",
            "requires_user_input": False,
            "evidence": {"major": major_dimensions, "fatal": fatal_dimensions},
        })

    if status == "major_revision" and fatal_dimensions:
        reasons.append({
            "file": scorecard_display,
            "message": "`major_revision` status is inconsistent with fatal reviewer issues.",
            "suggestion": "Use needs_data or reject_rewrite when flaws are fatal to the current paper.",
            "requires_user_input": False,
            "evidence": {"fatal": fatal_dimensions},
        })

    if status == "needs_data" and "data_acquisition" not in routes:
        reasons.append({
            "file": scorecard_display,
            "message": "`needs_data` status must include at least one scorecard route to `data_acquisition`.",
            "suggestion": "Add a required action and route that sends the workflow back to data acquisition.",
            "requires_user_input": False,
        })

    if status == "reject_rewrite" and not fatal_dimensions:
        reasons.append({
            "file": scorecard_display,
            "message": "`reject_rewrite` status requires at least one fatal scorecard dimension.",
            "suggestion": "Either document the fatal flaw or use major_revision instead.",
            "requires_user_input": False,
        })

    if status in {"major_revision", "needs_data", "reject_rewrite"} and not (major_dimensions or fatal_dimensions or failing_dimensions):
        reasons.append({
            "file": scorecard_display,
            "message": f"`{status}` status is not supported by any failing, major, or fatal scorecard dimension.",
            "suggestion": "Either document the serious issue in the scorecard or choose a less severe status.",
            "requires_user_input": False,
        })

    passed = not reasons
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"Strict review scorecard is valid; status={status}, mean={mean_score:.2f}."
            if passed
            else f"Strict review scorecard has {len(reasons)} issue(s)."
        ),
        "score": 1.0 if passed else max(0.0, 1.0 - min(len(reasons), 10) / 10),
        "reasons": reasons,
        "metadata": {
            "scorecard": scorecard_display,
            "report": report_display,
            "context": context,
            "status": status,
            "row_count": len(rows),
            "required_dimensions": required_dimensions,
            "missing_dimensions": missing_dimensions,
            "mean_score": mean_score,
            "min_accept_mean": min_accept_mean,
            "min_accept_score": min_accept_score,
            "failing_dimensions": failing_dimensions,
            "major_dimensions": major_dimensions,
            "fatal_dimensions": fatal_dimensions,
            "routes": sorted(routes),
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
