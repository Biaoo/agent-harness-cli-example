# Agent Harness CLI Research Workflow Example

[English](README.md) | [简体中文](README.zh-CN.md)

This repository is a runnable example for
[Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli). It shows
how the workflow-controller mode can drive a long-running AI-IE research task
through explicit states, checks, routing decisions, and Codex Stop hook
continuation.

The repository contains only this research workflow example.

## Workflow Goal

The workflow turns a rough AI-IE research idea into a complete research package:

```text
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
Research Complete
```

The hard routing rule is:

```text
Either the work produces a main-text-level insight, or it loops back for repair.
Do not route to SI-only digestion, downgrade publication, or a weaker fallback paper.
```

## Harness Engineering Flow

1. Codex works on the active research artifact under `research/ai-ie/`.
2. The project-level Stop hook runs `agent-harness step`.
3. The workflow controller validates the active node's artifacts and `Status:`
   value.
4. If the node fails, the hook blocks and tells Codex what to repair.
5. If exactly one transition matches, the workflow state advances and the hook
   blocks with the next-stage instruction.
6. If multiple transitions match, the state enters `choosing`; Codex must inspect
   `agent-harness options` and run `agent-harness choose`.
7. The hook stops blocking only after the terminal workflow node completes.

## Try It

Start a Codex session in this directory and ask:

```text
Research this idea with the AI-IE research workflow:

<your research idea>
```

`AGENTS.md` contains the project-level workflow instructions, so the user does
not need to paste the workflow protocol into the prompt.

When Codex attempts to stop, `.codex/hooks.json` runs:

```bash
bash "$(git rev-parse --show-toplevel)/.codex/hooks/run-agent-harness-check.sh"
```

That script calls:

```bash
agent-harness step --task workflows/ai-ie-research.json --report-id research-latest --hook-json
```

During local development, the hook automatically uses the sibling checkout at
`agent-harness` if it is installed, otherwise it falls back to:

```bash
uvx --from agent-harness-cli==0.1.2 agent-harness
```

## Useful Commands

Validate the workflow:

```bash
agent-harness validate-workflow --task workflows/ai-ie-research.json
```

Run one workflow step:

```bash
agent-harness step --task workflows/ai-ie-research.json --hook-json
```

Inspect state:

```bash
agent-harness status --state .agent-harness/ai-ie-research-state.json
```

Inspect and choose a model-choice transition:

```bash
agent-harness options --state .agent-harness/ai-ie-research-state.json
agent-harness choose <transition-id> --state .agent-harness/ai-ie-research-state.json --reason "why this route is appropriate"
```

View the latest workflow report:

```bash
agent-harness view research-latest --report-dir reports/research-workflow --failed-only
```

## Acceptance Surface

The workflow uses two deterministic check scripts:

| Check | Purpose | Source of truth |
| --- | --- | --- |
| `check_markdown_sections.py` | Verifies that the active Markdown artifact exists, has required headings, and is substantive enough for that node. | `workflows/ai-ie-research.json` |
| `check_research_status.py` | Reads the artifact's `Status: <value>` line and exposes it as `metadata.status` for transition conditions. | `workflows/ai-ie-research.json` |

The workflow graph owns routing. The check scripts stay narrow and deterministic.

## Project Layout

```text
AGENTS.md                            Project instructions for Codex.
.agents/
  skills/harness-workflow-runner/    Project-level workflow runner skill.
.codex/
  hooks.json                         Project-level Stop hook config.
  hooks/run-agent-harness-check.sh   Workflow Stop hook entry point.
checks/
  check_markdown_sections.py         Markdown artifact structure check.
  check_research_status.py           Workflow routing status check.
workflows/
  ai-ie-research.json                Research workflow graph.
research/
  ai-ie/README.md                    Artifact contract and allowed statuses.
pyproject.toml                       Example package metadata.
```

Generated runtime files are ignored:

```text
.agent-harness/
reports/
```

## Design Notes

- The example keeps domain logic in the workspace: workflow spec, artifact
  contracts, and check scripts.
- The CLI supplies state control, validation, reports, transition application,
  and hook JSON.
- The Stop hook returns `decision: "block"` until the research workflow reaches
  `research_complete`.
- The example is dependency-free and uses only Python standard library checks.
