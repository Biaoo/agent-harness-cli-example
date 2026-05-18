# AI-IE Main-Insight Research Workflow

This directory is the workspace for the workflow example in
`workflows/ai-ie-research.json`.

The task is to drive an AI-IE research idea through a full research pipeline:
idea intake, knowledge mapping, insight discovery, research design, data
acquisition, analysis, insight verification, results architecture, manuscript
drafting, reader/evidence audit, and submission packaging.

The hard routing rule is:

```text
Either the work produces a main-text-level insight, or it loops back for repair.
Do not route to SI-only digestion, downgrade publication, or a weaker fallback paper.
```

## How To Work

Start a Codex session in the repository root and ask it to run the AI-IE
research workflow. The first active node is `idea_intake`; Codex should create:

```text
research/ai-ie/idea_brief.md
```

When Codex tries to stop, the project Stop hook runs:

```bash
agent-harness step --task workflows/ai-ie-research.json --hook-json
```

The harness validates the active node, updates
`.agent-harness/ai-ie-research-state.json`, writes a report under
`reports/research-workflow/`, and blocks Codex until the workflow reaches the
terminal node.

## Status Contract

Every workflow artifact must include a line like:

```text
Status: clarified
```

The status drives routing. Use only the statuses allowed by the current
workflow node.

## Quality Gate Layers

The workflow does not rely on structure alone. Critical nodes use layered gates:

1. Structure checks verify artifact existence, required headings, and minimum
   content length.
2. Stage checklist checks verify stage completion, status justification, and
   whether the artifact can honestly enter the next stage.
3. Deep quality checklist checks verify research-object modeling, true
   information delta, method-claim fit, data provenance, evidence boundaries,
   alternative explanations, and whether the insight can carry a main paper.

Checklist checks call local `codex exec` to fill Markdown checklists from
`checklists/research/`, then parse the checklist into harness JSON. Set
`AGENT_HARNESS_ENABLE_LLM=0` only when debugging deterministic checks.

## Artifact Contracts

`idea_intake`

```text
research/ai-ie/idea_brief.md
Status: clarified | too_broad | needs_user_authority
Required headings:
# Idea Brief
## World Phenomenon
## Research Question
## Idea Anchor
## Scope Boundary
## Status
```

`world_knowledge_map`

```text
research/ai-ie/knowledge_map.md
Status: searching | mapped | partial_coverage | blocked | stale
Required headings:
# World Knowledge Map
## Search Log
## Literature Matrix
## What Existing Work Explains
## What Existing Work Does Not Explain
## Knowledge Gaps
## Status
```

`insight_direction_discovery`

```text
research/ai-ie/insight_direction.md
Status: candidate | promising | weak | derivative | no_delta | blocked
Required headings:
# Insight Direction Discovery
## Candidate Information Delta
## Information Delta Spine
## Why Existing Work Does Not Already Cover It
## Competing Directions
## Status
```

`research_design`

```text
research/ai-ie/research_design.md
Status: designed | evidence_needed | data_needed | method_uncertain | infeasible | ready_for_data
Required headings:
# Research Design
## Research Question
## Hypothesis or Mechanism
## Evidence Design
## Variables and Proxies
## Identification or Comparison Strategy
## Data Requirements
## Status
```

`data_acquisition`

```text
research/ai-ie/data_acquisition.md
Status: searching | acquired | substitute_found | insufficient | biased | permission_blocked | infeasible
Required headings:
# Data Acquisition
## Source Register
## Acquisition Log
## Data Manifest
## Data Fitness for Research Design
## Bias or Permission Risks
## Status
```

`analysis`

```text
research/ai-ie/analysis_findings.md
Status: running | produced | robust | surprising | null | noisy | weak | failed
Required headings:
# Analysis Findings
## Run Manifest
## Outputs
## Observed Pattern
## Robustness or Sensitivity
## Interpretation
## Status
```

`insight_verification`

```text
research/ai-ie/insight_verification.md
Status: confirmed_insight | weak | already_known | derivative | no_delta | contradicted | blocked
Required headings:
# Insight Verification
## Main-text Insight Claim
## Novelty Verification
## Claim Strength
## Alternative Explanations
## Reject Downgrade Path
## Status
```

`results_architecture`

```text
research/ai-ie/results_architecture.md
Status: admitted | repair_needed | blocked
Required headings:
# Results Architecture
## Results Chain
## Result Modules
## Evidence Boundary
## Repair Log
## Status
```

`figures_manuscript`

```text
research/ai-ie/manuscript.md
Status: drafting | figures_synced | needs_repair | blocked
Required headings:
# Manuscript Draft
## Abstract
## Introduction
## Results
## Figure Plan
## Claim Map
## Evidence Boundaries
## Status
```

`reader_evidence_audit`

```text
research/ai-ie/reader_evidence_audit.md
Status: pending | passed | needs_repair | blocked
Required headings:
# Reader / Evidence Audit
## Reader Comprehension
## Evidence Trust
## Citation Trace
## Readiness Judgment
## Status
```

`submission_package`

```text
research/ai-ie/submission_package.md
Status: package_ready | waiting_user_authority | submitted_ready | blocked
Required headings:
# Submission Package
## Manuscript
## Figures
## References
## Declarations
## Cover Letter
## User Authority
## Status
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

If a gate enters `choosing`, inspect and choose:

```bash
agent-harness options --state .agent-harness/ai-ie-research-state.json
agent-harness choose <transition-id> --state .agent-harness/ai-ie-research-state.json --reason "why this route is appropriate"
```
