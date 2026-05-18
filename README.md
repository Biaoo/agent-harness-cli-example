# Agent Harness CLI Research Workflow Example

[English](README.md) | [简体中文](README.zh-CN.md)

This repository is a runnable example for
[Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli). It shows
how the workflow-controller mode can drive a long-running research task
through explicit states, checks, routing decisions, and Codex Stop hook
continuation.

The repository contains only this research workflow example.

## Workflow Goal

The workflow turns a rough research idea into a topic-scoped research package:

```text
Research Context
Idea Intake
World Knowledge Map
Insight Direction Discovery
Research Design
Data Acquisition
Analysis
Insight Verification
Results Architecture
Figures + Manuscript
Reader / Evidence Audit
Submission Package
Strict Paper Review
Final Quality Review
Research Complete
```

The hard routing rule is:

```text
Either the work produces a main-text-level insight, or it loops back for repair.
Do not route to SI-only digestion, downgrade publication, or a weaker fallback paper.
```

## Harness Engineering Flow

1. Codex creates `research/context.json` with the runtime topic metadata.
2. Codex works on the active research artifact under `research/<topic_slug>/`.
3. The project-level Stop hook runs `agent-harness step`.
4. The workflow controller validates the active node's artifacts and `Status:`
   value.
5. If the node fails, the hook blocks and tells Codex what to repair.
6. If exactly one transition matches, the workflow state advances and the hook
   blocks with the next-stage instruction.
7. If multiple transitions match, the state enters `choosing`; Codex must inspect
   `agent-harness options` and run `agent-harness choose`.
8. The hook stops blocking only after the terminal workflow node completes.

## Try It

Start a Codex session in this directory and ask:

```text
Research this idea with the research workflow:

<your research idea>
```

`AGENTS.md` contains the project-level workflow instructions, so the user does
not need to paste the workflow protocol into the prompt.

On the first step, Codex creates:

```json
{
  "topic_title": "Human-readable research topic",
  "topic_slug": "lower-kebab-topic-slug",
  "research_dir": "research/lower-kebab-topic-slug"
}
```

All later artifact paths in the workflow use `research/{topic_slug}/...`; the
check scripts resolve that placeholder from `research/context.json`.

When Codex attempts to stop, `.codex/hooks.json` runs:

```bash
bash "$(git rev-parse --show-toplevel)/.codex/hooks/run-agent-harness-check.sh"
```

That script calls:

```bash
agent-harness step --task workflows/research.json --report-id research-latest --hook-json
```

The hook uses `agent-harness` if it is installed. Otherwise it falls back to:

```bash
uvx --from agent-harness-cli==0.1.2 agent-harness
```

## Useful Commands

Validate the workflow:

```bash
agent-harness validate-workflow --task workflows/research.json
```

Run one workflow step:

```bash
agent-harness step --task workflows/research.json --hook-json
```

Inspect state:

```bash
agent-harness status --state .agent-harness/research-state.json
```

Inspect and choose a model-choice transition:

```bash
agent-harness options --state .agent-harness/research-state.json
agent-harness choose <transition-id> --state .agent-harness/research-state.json --reason "why this route is appropriate"
```

View the latest workflow report:

```bash
agent-harness view research-latest --report-dir reports/research --failed-only
```

## Acceptance Surface

The workflow uses four layers of gates:

| Layer | Purpose | Implementation |
| --- | --- | --- |
| Structure | Ensure the active artifact exists, has required headings, and has enough substance to inspect. | `check_markdown_sections.py` |
| Stage semantics | Verify that the stage is genuinely complete and the chosen `Status:` is justified. | `check_research_checklist.py` + `checklists/research/stage/*.md` |
| Deep research quality | Check research-object modeling, true information delta, method-claim match, data provenance, evidence boundaries, alternative explanations, figure/table quality, publication-style prose, and manuscript argument quality. | `check_research_checklist.py` + `checklists/research/deep/*.md` |
| Evidence controls | Require source evidence packs, data fitness matrices, claim-evidence traces, generated figure/table assets, reader-facing citations/references, strict reviewer scorecards, claim-strength calibration, link integrity, overclaim review, and final quality reporting. | `check_research_csv_contract.py`, `check_research_trace_links.py`, `check_research_figure_assets.py`, `check_research_manuscript_publication_style.py`, `check_research_review_scorecard.py`, dedicated checklists |

The workflow uses these check scripts:

| Check | Purpose | Source of truth |
| --- | --- | --- |
| `check_research_context.py` | Verifies `research/context.json` and the matching topic directory. | `research/context.json` |
| `check_markdown_sections.py` | Verifies that the active Markdown artifact exists, has required headings, and is substantive enough for that node. | `workflows/research.json` |
| `check_research_status.py` | Reads the artifact's `Status: <value>` line and exposes it as `metadata.status` for transition conditions. | `workflows/research.json` |
| `check_research_csv_contract.py` | Verifies required CSV evidence-control artifacts, columns, row counts, non-empty cells, and enum values. | `workflows/research.json` |
| `check_research_trace_links.py` | Verifies claim trace rows reference existing source IDs and data-fitness claim IDs. | `source_evidence_pack.csv`, `claim_evidence_trace.csv`, `data_fitness_matrix.csv` |
| `check_research_figure_assets.py` | Verifies generated figure/table assets exist under the topic figures directory and are referenced by the manuscript. | `figure_manifest.csv`, `manuscript.md` |
| `check_research_manuscript_form.py` | Verifies the manuscript is developed as paper-style prose instead of memo bullets or a figure plan. | `manuscript.md` |
| `check_research_manuscript_publication_style.py` | Verifies the reader-facing manuscript body does not leak harness internals and includes publication-style citations, references, and named result subsections. | `manuscript.md` |
| `check_research_review_scorecard.py` | Verifies strict reviewer scorecards, score thresholds, routes, and accept/revision consistency. | `strict_paper_review.md`, `reviewer_scorecard.csv` |
| `check_research_checklist.py` | Calls local `codex exec` to fill a Markdown checklist, then parses checked/unchecked items into harness JSON. | `checklists/research/` |

The workflow graph owns routing. Structure and status checks are deterministic.
Checklist checks are semantic quality gates; set `AGENT_HARNESS_ENABLE_LLM=0`
only for deterministic-only debugging.

`research/context.json` is the runtime path resolver. A single checkout can run
different topics over time by changing `topic_slug`; artifacts stay isolated
under `research/<topic_slug>/`.

## Project Layout

```text
AGENTS.md                            Project instructions for Codex.
.agents/
  skills/research-workflow-runner/   Project-level research workflow skill.
.codex/
  hooks.json                         Project-level Stop hook config.
  hooks/run-agent-harness-check.sh   Workflow Stop hook entry point.
checks/
  check_research_context.py          Runtime topic context check.
  check_markdown_sections.py         Markdown artifact structure check.
  check_research_status.py           Workflow routing status check.
  check_research_csv_contract.py     CSV evidence-control contract check.
  check_research_trace_links.py      Claim/source/data link integrity check.
  check_research_figure_assets.py    Generated figure/table asset check.
  check_research_manuscript_form.py  Paper-form manuscript check.
  check_research_manuscript_publication_style.py
                                      Reader-facing manuscript style check.
  check_research_review_scorecard.py Strict reviewer scorecard check.
  check_research_checklist.py        Markdown checklist semantic/deep gate.
  local_codex_judge.py               Local Codex checklist judge helper.
  research_paths.py                  Shared topic path resolver.
checklists/
  research/stage/                    Stage completion checklist templates.
  research/deep/                     Deep research quality checklist templates.
workflows/
  research.json                      Research workflow graph.
research/
  README.md                          Artifact contract and allowed statuses.
  context.json                       Runtime topic context, generated by Codex.
  <topic_slug>/                      Topic-specific research artifacts.
pyproject.toml                       Example package metadata.
```

Generated runtime files are ignored:

```text
.agent-harness/
reports/
research/context.json
research/<topic_slug>/
```

## Design Notes

- The example keeps domain logic in the workspace: workflow spec, artifact
  contracts, checklists, and check scripts.
- The CLI supplies state control, validation, reports, transition application,
  and hook JSON.
- The Stop hook returns `decision: "block"` until the research workflow reaches
  `research_complete`.
- Check scripts use the Python standard library. Semantic/deep gates require a
  usable local Codex CLI because they call `codex exec`.
