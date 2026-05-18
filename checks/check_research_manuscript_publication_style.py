from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from research_paths import resolve_config_path


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
SOURCE_ID_RE = re.compile(r"(?<![A-Za-z0-9])S\d+(?![A-Za-z0-9])")
CLAIM_ID_RE = re.compile(r"(?<![A-Za-z0-9])C\d+(?![A-Za-z0-9])")
ASSET_ID_RE = re.compile(r"(?<![A-Za-z0-9])[FT]\d+(?![A-Za-z0-9])")
SOURCE_ID_CITATION_RE = re.compile(r"\[(?:S\d+(?:\s*[-,;]\s*S?\d+)*)\]")
LOCAL_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"(?:research|reports|checks|checklists|workflows|\.agent-harness|\.agents|\.codex)/"
    r"[^\s)`，。；；,]+"
)
ARTIFACT_RE = re.compile(
    r"\b(?:"
    r"source_evidence_pack|claim_evidence_trace|data_fitness_matrix|"
    r"figure_manifest|figure_blueprint|quality_report|research/context|"
    r"generate_figures|workflow|checklist|metadata\.status"
    r")\b",
    re.IGNORECASE,
)
AUDIT_PROSE_RE = re.compile(
    r"(?:"
    r"路径为|"
    r"Figure\s+\d+\s*/\s*[FT]\d+|"
    r"Table\s+\d+\s*/\s*T\d+|"
    r"Claim role|Evidence basis|Boundary:|"
    r"第一组结果|第二组结果|第三组结果|第四组结果|第五组结果|第六组结果|"
    r"第七组结果|第八组结果|第九组结果|第十组结果"
    r")",
    re.IGNORECASE,
)
READER_CITATION_RE = re.compile(
    r"(?:"
    r"[A-Z][A-Za-z][A-Za-z\-]+(?:\s+et\s+al\.)?\s+\((?:19|20)\d{2}[a-z]?\)|"
    r"\([A-Z][^)\n]{2,80},\s*(?:19|20)\d{2}[a-z]?\)|"
    r"Regulation\s+\(EU\)\s+\d{4}/\d+|"
    r"Implementing\s+Regulation\s+\(EU\)\s+\d{4}/\d+"
    r")"
)


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


def section_bounds(markdown: str) -> dict[str, tuple[int, int, int]]:
    matches = list(HEADING_RE.finditer(markdown))
    bounds: dict[str, tuple[int, int, int]] = {}
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        end = len(markdown)
        for later in matches[index + 1:]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        bounds[title] = (match.end(), end, level)
    return bounds


def line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def first_matches(pattern: re.Pattern[str], text: str, limit: int = 5) -> list[re.Match[str]]:
    return list(pattern.finditer(text))[:limit]


def reference_entries(section: str) -> list[str]:
    entries: list[str] = []
    blocks = re.split(r"\n\s*\n", section.strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].startswith("#"):
            continue
        if len(lines) == 1 and re.match(r"^(Status|References)\b", lines[0], re.IGNORECASE):
            continue
        if re.match(r"^(?:[-*]|\d+[.)])\s+", lines[0]) or READER_CITATION_RE.search(" ".join(lines)):
            entries.append(" ".join(lines))
    return entries


def subsection_count(section: str) -> tuple[int, list[str]]:
    headings = []
    for match in HEADING_RE.finditer(section):
        if len(match.group(1)) == 3:
            headings.append(match.group(2).strip())
    return len(headings), headings


def add_pattern_reasons(
    *,
    reasons: list[dict[str, Any]],
    pattern: re.Pattern[str],
    text: str,
    section_name: str,
    display_path: str,
    message: str,
    suggestion: str,
    line_offset: int = 0,
) -> int:
    matches = first_matches(pattern, text)
    for match in matches:
        reasons.append({
            "file": display_path,
            "line": line_for_offset(text, match.start()) + line_offset,
            "message": f"{message} in `{section_name}`: `{match.group(0)}`.",
            "suggestion": suggestion,
            "requires_user_input": False,
        })
    return len(list(pattern.finditer(text)))


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    root = Path(input_data["root"])
    check = input_data["check"]
    config = check.get("config", {})
    name = check.get("name", "research_manuscript_publication_style")
    severity = check.get("severity", "error")
    raw_path = str(config.get("path", ""))
    main_sections = [str(item) for item in config.get("main_sections", [
        "Abstract",
        "Introduction",
        "Methods",
        "Results",
        "Discussion",
        "Conclusion",
    ])]
    required_reference_section = bool(config.get("required_reference_section", True))
    min_reference_entries = int(config.get("min_reference_entries", 8))
    min_reader_facing_citations = int(config.get("min_reader_facing_citations", 6))
    subsection_requirements = [
        {
            "section": str(item.get("section", "")),
            "min_subsections": int(item.get("min_subsections", 0)),
        }
        for item in config.get("subsection_requirements", [])
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
                "suggestion": "Create manuscript.md before running publication-style checks.",
                "requires_user_input": False,
            }],
            metadata={"path": display_path, "missing": True, "context": context},
        )

    text = path.read_text(encoding="utf-8")
    bounds = section_bounds(text)
    reasons: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {
        "path": display_path,
        "context": context,
        "main_sections": main_sections,
        "section_metrics": {},
    }

    main_text_parts: list[str] = []
    for section_name in main_sections:
        if section_name not in bounds:
            reasons.append({
                "file": display_path,
                "message": f"Missing main manuscript section `## {section_name}`.",
                "suggestion": "Add the section as a reader-facing paper section.",
                "requires_user_input": False,
            })
            continue
        start, end, _ = bounds[section_name]
        section = text[start:end]
        line_offset = line_for_offset(text, start) - 1
        main_text_parts.append(section)
        metrics = {
            "local_path_mentions": add_pattern_reasons(
                reasons=reasons,
                pattern=LOCAL_PATH_RE,
                text=section,
                section_name=section_name,
                display_path=display_path,
                message="Local project path leaked into main prose",
                suggestion="Remove local file paths from main paper prose; keep asset paths only in the Figures and Tables manifest area.",
                line_offset=line_offset,
            ),
            "artifact_mentions": add_pattern_reasons(
                reasons=reasons,
                pattern=ARTIFACT_RE,
                text=section,
                section_name=section_name,
                display_path=display_path,
                message="Harness/internal artifact language leaked into main prose",
                suggestion="Rewrite this as reader-facing methods or evidence language; keep harness artifact names out of the paper body.",
                line_offset=line_offset,
            ),
            "source_id_mentions": add_pattern_reasons(
                reasons=reasons,
                pattern=SOURCE_ID_RE,
                text=section,
                section_name=section_name,
                display_path=display_path,
                message="Internal source ID leaked into main prose",
                suggestion="Replace source IDs with reader-facing citations and full references.",
                line_offset=line_offset,
            ),
            "source_id_citations": add_pattern_reasons(
                reasons=reasons,
                pattern=SOURCE_ID_CITATION_RE,
                text=section,
                section_name=section_name,
                display_path=display_path,
                message="Internal source-ID citation used in main prose",
                suggestion="Use author-year, legal-document, or numbered reference citations instead of harness source IDs.",
                line_offset=line_offset,
            ),
            "claim_id_mentions": add_pattern_reasons(
                reasons=reasons,
                pattern=CLAIM_ID_RE,
                text=section,
                section_name=section_name,
                display_path=display_path,
                message="Internal claim ID leaked into main prose",
                suggestion="Write the claim in natural language; keep claim IDs in the Claim Map or audit material.",
                line_offset=line_offset,
            ),
            "asset_id_mentions": add_pattern_reasons(
                reasons=reasons,
                pattern=ASSET_ID_RE,
                text=section,
                section_name=section_name,
                display_path=display_path,
                message="Internal figure/table asset ID leaked into main prose",
                suggestion="Use `Figure 1` or `Table 1` in paper prose; reserve asset IDs for the manifest.",
                line_offset=line_offset,
            ),
            "audit_prose_mentions": add_pattern_reasons(
                reasons=reasons,
                pattern=AUDIT_PROSE_RE,
                text=section,
                section_name=section_name,
                display_path=display_path,
                message="Audit/report-style phrase found in main prose",
                suggestion="Rewrite this as normal paper argument rather than workflow or manifest narration.",
                line_offset=line_offset,
            ),
        }
        metadata["section_metrics"][section_name] = metrics

    joined_main = "\n\n".join(main_text_parts)
    reader_citations = READER_CITATION_RE.findall(joined_main)
    metadata["reader_facing_citation_count"] = len(reader_citations)
    metadata["min_reader_facing_citations"] = min_reader_facing_citations
    if len(reader_citations) < min_reader_facing_citations:
        reasons.append({
            "file": display_path,
            "message": (
                f"Main prose has {len(reader_citations)} reader-facing citation(s), "
                f"below the required minimum {min_reader_facing_citations}."
            ),
            "suggestion": "Replace internal source IDs with author-year, legal-document, or numbered citations that readers can resolve in References.",
            "requires_user_input": False,
        })

    if required_reference_section:
        if "References" not in bounds:
            reasons.append({
                "file": display_path,
                "message": "Missing required `## References` section.",
                "suggestion": "Add reader-facing references; do not leave sources only as internal source IDs.",
                "requires_user_input": False,
            })
            metadata["reference_entries"] = 0
        else:
            start, end, _ = bounds["References"]
            entries = reference_entries(text[start:end])
            metadata["reference_entries"] = len(entries)
            metadata["min_reference_entries"] = min_reference_entries
            if len(entries) < min_reference_entries:
                reasons.append({
                    "file": display_path,
                    "message": (
                        f"`## References` has {len(entries)} reference entrie(s), "
                        f"below the required minimum {min_reference_entries}."
                    ),
                    "suggestion": "Add full bibliographic or legal-document references for the sources cited in the manuscript.",
                    "requires_user_input": False,
                })

    metadata["subsection_metrics"] = {}
    for requirement in subsection_requirements:
        section_name = requirement["section"]
        min_subsections = requirement["min_subsections"]
        if not section_name:
            continue
        if section_name not in bounds:
            continue
        start, end, _ = bounds[section_name]
        count, headings = subsection_count(text[start:end])
        metadata["subsection_metrics"][section_name] = {
            "count": count,
            "min_subsections": min_subsections,
            "headings": headings,
        }
        if count < min_subsections:
            reasons.append({
                "file": display_path,
                "message": (
                    f"`## {section_name}` has {count} level-3 subsection(s), "
                    f"below the required minimum {min_subsections}."
                ),
                "suggestion": "Organize this section with named conceptual subheadings, not numbered gate or figure groups.",
                "requires_user_input": False,
            })

    passed = not reasons
    return {
        "check": name,
        "passed": passed,
        "severity": severity,
        "summary": (
            "Manuscript publication style is reader-facing."
            if passed
            else f"Manuscript publication style has {len(reasons)} issue(s)."
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
