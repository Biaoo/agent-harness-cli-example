from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from research_paths import resolve_config_path


WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*|[\u4e00-\u9fff]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


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


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def section_text(markdown: str, heading: str) -> str:
    target = f"## {heading}"
    start = None
    for match in HEADING_RE.finditer(markdown):
        full_heading = match.group(0).strip()
        if full_heading == target:
            start = match.end()
            continue
        if start is not None and match.group(1) == "##":
            return markdown[start:match.start()].strip()
    if start is None:
        return ""
    return markdown[start:].strip()


def narrative_paragraphs(section: str, min_chars: int) -> list[str]:
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", section.strip()):
        stripped = block.strip()
        if len(stripped) < min_chars:
            continue
        if stripped.startswith(("#", "-", "*", "|", "```")):
            continue
        if re.match(r"^(Status|Figure|Table|Box)\s*[:\d]", stripped, re.IGNORECASE):
            continue
        if re.match(r"^Result\s+\d+\s*[:.]", stripped, re.IGNORECASE):
            continue
        paragraphs.append(stripped)
    return paragraphs


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_manuscript_form")
    severity = check.get("severity", "error")
    raw_path = str(config.get("path", ""))
    min_words = int(config.get("min_words", 1800))
    paragraph_min_chars = int(config.get("paragraph_min_chars", 180))
    min_figure_refs = int(config.get("min_figure_refs", 1))
    min_table_refs = int(config.get("min_table_refs", 1))
    max_outline_result_lines = int(config.get("max_outline_result_lines", 0))
    required_sections = [
        {"heading": str(item.get("heading", "")), "min_paragraphs": int(item.get("min_paragraphs", 1))}
        for item in config.get("required_sections", [])
    ]

    if not raw_path:
        return fail_result(
            name=name,
            severity=severity,
            summary="Manuscript path is not configured.",
            reasons=[{
                "message": "check.config.path is required.",
                "suggestion": "Set check.config.path to the manuscript artifact path.",
                "requires_user_input": False,
            }],
        )

    display_path, path, context = resolve_config_path(root, raw_path, config)
    if not path.exists():
        return fail_result(
            name=name,
            severity=severity,
            summary="Manuscript artifact is missing.",
            reasons=[{
                "file": display_path,
                "message": "The required manuscript artifact does not exist.",
                "suggestion": "Create manuscript.md with paper-style sections and narrative prose.",
                "requires_user_input": False,
            }],
            metadata={"path": display_path, "missing": True, "context": context},
        )

    text = path.read_text(encoding="utf-8")
    count = word_count(text)
    reasons: list[dict[str, Any]] = []

    if count < min_words:
        reasons.append({
            "file": display_path,
            "message": f"Manuscript has {count} word/token unit(s), below the required minimum {min_words}.",
            "suggestion": "Expand the draft into paper-style prose with methods, results, discussion, and conclusion.",
            "requires_user_input": False,
            "evidence": {"actual_words": count, "min_words": min_words},
        })

    section_metadata: dict[str, Any] = {}
    for requirement in required_sections:
        heading = requirement["heading"]
        min_paragraphs = requirement["min_paragraphs"]
        body = section_text(text, heading)
        paragraphs = narrative_paragraphs(body, paragraph_min_chars)
        section_metadata[heading] = {
            "paragraph_count": len(paragraphs),
            "min_paragraphs": min_paragraphs,
        }
        if not body:
            reasons.append({
                "file": display_path,
                "message": f"Missing required manuscript section: ## {heading}",
                "suggestion": f"Add a `## {heading}` section with paper-style narrative prose.",
                "requires_user_input": False,
            })
        elif len(paragraphs) < min_paragraphs:
            reasons.append({
                "file": display_path,
                "message": (
                    f"`## {heading}` has {len(paragraphs)} substantive narrative paragraph(s), "
                    f"below the required minimum {min_paragraphs}."
                ),
                "suggestion": "Replace outline bullets or memo fragments with developed paragraphs.",
                "requires_user_input": False,
            })

    outline_result_lines = re.findall(r"(?im)^Result\s+\d+\s*[:.]", text)
    if len(outline_result_lines) > max_outline_result_lines:
        reasons.append({
            "file": display_path,
            "message": (
                f"Manuscript contains {len(outline_result_lines)} outline-style `Result N:` line(s), "
                f"above the allowed maximum {max_outline_result_lines}."
            ),
            "suggestion": "Turn numbered result notes into integrated Results prose with transitions and interpretation.",
            "requires_user_input": False,
        })

    figure_refs = sorted(set(re.findall(r"\bFigure\s+\d+\b", text, flags=re.IGNORECASE)))
    table_refs = sorted(set(re.findall(r"\bTable\s+\d+\b", text, flags=re.IGNORECASE)))
    if len(figure_refs) < min_figure_refs:
        reasons.append({
            "file": display_path,
            "message": f"Manuscript references {len(figure_refs)} figure(s), below the required minimum {min_figure_refs}.",
            "suggestion": "Discuss generated figures in the Results or Discussion prose.",
            "requires_user_input": False,
        })
    if len(table_refs) < min_table_refs:
        reasons.append({
            "file": display_path,
            "message": f"Manuscript references {len(table_refs)} table(s), below the required minimum {min_table_refs}.",
            "suggestion": "Reference generated or computed tables where they support claims.",
            "requires_user_input": False,
        })

    passed = not reasons
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            "Manuscript form is paper-like enough for review."
            if passed
            else f"Manuscript form has {len(reasons)} issue(s)."
        ),
        "score": 1.0 if passed else max(0.0, 1.0 - min(len(reasons), 10) / 10),
        "reasons": reasons,
        "metadata": {
            "path": display_path,
            "context": context,
            "word_count": count,
            "min_words": min_words,
            "sections": section_metadata,
            "figure_refs": figure_refs,
            "table_refs": table_refs,
            "outline_result_lines": len(outline_result_lines),
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
