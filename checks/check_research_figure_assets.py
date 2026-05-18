from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from research_paths import expand_research_path, resolve, resolve_config_path


REQUIRED_COLUMNS = [
    "asset_id",
    "asset_type",
    "title",
    "path",
    "generation_method",
    "claim_ids",
    "source_ids",
    "caption",
    "status",
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


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
        return reader.fieldnames or [], rows


def mention_present(text: str, *needles: str) -> bool:
    normalized = text.lower()
    return any(needle and needle.lower() in normalized for needle in needles)


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_figure_assets")
    severity = check.get("severity", "error")

    manifest_raw = str(config.get("manifest", ""))
    manuscript_raw = str(config.get("manuscript", ""))
    min_assets = int(config.get("min_assets", 1))
    min_figures = int(config.get("min_figures", 1))
    min_tables = int(config.get("min_tables", 0))
    min_file_bytes = int(config.get("min_file_bytes", 64))
    asset_dir_raw = str(config.get("asset_dir", ""))
    allowed_asset_types = set(config.get("allowed_asset_types", ["figure", "table", "box"]))
    allowed_generation_methods = set(config.get("allowed_generation_methods", [
        "python",
        "imagegen",
        "manual_svg",
        "markdown_table",
    ]))
    publishable_statuses = set(config.get("publishable_statuses", ["generated", "referenced"]))

    if not manifest_raw or not manuscript_raw:
        return fail_result(
            name=name,
            severity=severity,
            summary="Figure asset check is not fully configured.",
            reasons=[{
                "message": "check.config.manifest and check.config.manuscript are required.",
                "suggestion": "Set both paths in the workflow check config.",
                "requires_user_input": False,
            }],
        )

    manifest_display, manifest_path, context = resolve_config_path(root, manifest_raw, config)
    manuscript_display, manuscript_path, _ = resolve_config_path(root, manuscript_raw, config)
    if not manifest_path.exists():
        return fail_result(
            name=name,
            severity=severity,
            summary="Figure manifest is missing.",
            reasons=[{
                "file": manifest_display,
                "message": "The required figure_manifest.csv artifact does not exist.",
                "suggestion": "Create a figure manifest with one row per generated figure, table, or box.",
                "requires_user_input": False,
            }],
            metadata={"manifest": manifest_display, "missing": True, "context": context},
        )
    if not manuscript_path.exists():
        return fail_result(
            name=name,
            severity=severity,
            summary="Manuscript is missing.",
            reasons=[{
                "file": manuscript_display,
                "message": "The manuscript required for figure-reference checks does not exist.",
                "suggestion": "Create manuscript.md and reference each generated asset from it.",
                "requires_user_input": False,
            }],
            metadata={"manuscript": manuscript_display, "missing": True, "context": context},
        )

    try:
        columns, rows = read_csv(manifest_path)
    except csv.Error as exc:
        return fail_result(
            name=name,
            severity=severity,
            summary="Figure manifest cannot be parsed.",
            reasons=[{
                "file": manifest_display,
                "message": f"CSV parse error: {exc}",
                "suggestion": "Rewrite the manifest as valid CSV with a header row.",
                "requires_user_input": False,
            }],
            metadata={"manifest": manifest_display, "context": context},
        )

    manuscript_text = manuscript_path.read_text(encoding="utf-8")
    reasons: list[dict[str, Any]] = []
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
    for column in missing_columns:
        reasons.append({
            "file": manifest_display,
            "message": f"Missing required column: {column}",
            "suggestion": f"Add the `{column}` column to figure_manifest.csv.",
            "requires_user_input": False,
        })

    if len(rows) < min_assets:
        reasons.append({
            "file": manifest_display,
            "message": f"Manifest has {len(rows)} asset row(s), below the required minimum {min_assets}.",
            "suggestion": "Generate enough substantive figure/table assets for the manuscript.",
            "requires_user_input": False,
            "evidence": {"actual_assets": len(rows), "min_assets": min_assets},
        })

    figure_count = sum(1 for row in rows if row.get("asset_type") == "figure")
    table_count = sum(1 for row in rows if row.get("asset_type") == "table")
    if figure_count < min_figures:
        reasons.append({
            "file": manifest_display,
            "message": f"Manifest has {figure_count} figure row(s), below the required minimum {min_figures}.",
            "suggestion": "Generate at least one real figure file under the configured figures directory.",
            "requires_user_input": False,
        })
    if table_count < min_tables:
        reasons.append({
            "file": manifest_display,
            "message": f"Manifest has {table_count} table row(s), below the required minimum {min_tables}.",
            "suggestion": "Generate at least one table asset used by the manuscript.",
            "requires_user_input": False,
        })

    asset_dir_display = ""
    if asset_dir_raw:
        asset_dir_display = expand_research_path(asset_dir_raw, context).rstrip("/") + "/"

    for index, row in enumerate(rows, start=2):
        for column in REQUIRED_COLUMNS:
            if column in columns and not row.get(column):
                reasons.append({
                    "file": manifest_display,
                    "message": f"Row {index} has an empty `{column}` value.",
                    "suggestion": f"Fill `{column}` with a concrete value.",
                    "requires_user_input": False,
                })

        asset_id = row.get("asset_id", "")
        asset_type = row.get("asset_type", "")
        title = row.get("title", "")
        raw_asset_path = row.get("path", "")
        generation_method = row.get("generation_method", "")
        status = row.get("status", "")

        if asset_type and asset_type not in allowed_asset_types:
            reasons.append({
                "file": manifest_display,
                "message": f"Row {index} has unsupported asset_type `{asset_type}`.",
                "suggestion": f"Use one of: {', '.join(sorted(allowed_asset_types))}.",
                "requires_user_input": False,
            })
        if generation_method and generation_method not in allowed_generation_methods:
            reasons.append({
                "file": manifest_display,
                "message": f"Row {index} has unsupported generation_method `{generation_method}`.",
                "suggestion": f"Use one of: {', '.join(sorted(allowed_generation_methods))}.",
                "requires_user_input": False,
            })
        if status and status not in publishable_statuses:
            reasons.append({
                "file": manifest_display,
                "message": f"Row {index} status `{status}` is not publishable.",
                "suggestion": f"Use one of: {', '.join(sorted(publishable_statuses))} after the asset exists and is cited.",
                "requires_user_input": False,
            })

        if raw_asset_path:
            asset_display = expand_research_path(raw_asset_path, context)
            if asset_dir_display and not asset_display.startswith(asset_dir_display):
                reasons.append({
                    "file": manifest_display,
                    "message": f"Row {index} asset path is outside `{asset_dir_display}`.",
                    "suggestion": f"Save generated assets under `{asset_dir_display}`.",
                    "requires_user_input": False,
                    "evidence": {"asset_path": asset_display},
                })

            asset_path = resolve(root, asset_display)
            if not asset_path.exists():
                reasons.append({
                    "file": manifest_display,
                    "message": f"Row {index} asset file does not exist: {asset_display}",
                    "suggestion": "Generate the asset file before marking the manuscript figures as synced.",
                    "requires_user_input": False,
                })
            elif asset_path.is_file() and asset_path.stat().st_size < min_file_bytes:
                reasons.append({
                    "file": asset_display,
                    "message": f"Asset file is too small ({asset_path.stat().st_size} bytes).",
                    "suggestion": "Regenerate the asset as a substantive figure/table file.",
                    "requires_user_input": False,
                })

            if not mention_present(manuscript_text, asset_display, Path(asset_display).name):
                reasons.append({
                    "file": manuscript_display,
                    "message": f"Manuscript does not reference asset path `{asset_display}`.",
                    "suggestion": "Embed or link the asset in the manuscript near the claim it supports.",
                    "requires_user_input": False,
                })

        if asset_id and not mention_present(manuscript_text, asset_id):
            reasons.append({
                "file": manuscript_display,
                "message": f"Manuscript does not mention asset_id `{asset_id}`.",
                "suggestion": "Reference each manifest asset ID in the figure/table caption or surrounding prose.",
                "requires_user_input": False,
            })
        if title and not mention_present(manuscript_text, title):
            reasons.append({
                "file": manuscript_display,
                "message": f"Manuscript does not mention asset title `{title}`.",
                "suggestion": "Use the manifest title in the figure/table caption.",
                "requires_user_input": False,
            })

    passed = not reasons
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            f"Figure assets passed with {len(rows)} manifest row(s)."
            if passed
            else f"Figure assets have {len(reasons)} issue(s)."
        ),
        "score": 1.0 if passed else max(0.0, 1.0 - min(len(reasons), 10) / 10),
        "reasons": reasons,
        "metadata": {
            "manifest": manifest_display,
            "manuscript": manuscript_display,
            "context": context,
            "row_count": len(rows),
            "figure_count": figure_count,
            "table_count": table_count,
            "asset_dir": asset_dir_display,
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
