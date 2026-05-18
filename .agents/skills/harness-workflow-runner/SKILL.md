---
name: harness-workflow-runner
description: Use when running this repository's Research Agent Harness workflow from a user research idea, producing active-node artifacts, handling step/options/choose/approve/reject, and continuing until research_complete.
---

# Harness Workflow Runner

This repository has one workflow:

- Workflow spec: `workflows/research.json`
- Artifact contract: `research/README.md`
- Runtime context: `research/context.json`
- State path: `.agent-harness/research-state.json`
- Report directory: `reports/research`

Users should be able to start with a short prompt:

```text
Research this idea with the research workflow:

<idea>
```

Read `AGENTS.md` first. It is the project source of truth for how to operate the
workflow.

## Operating Loop

1. If state exists, continue from the active node. If no state exists, start at
   `research_context`.
2. In `research_context`, create `research/context.json` and the matching
   `research/<topic_slug>/` directory from the user's idea.
3. Read the active node's artifact contract in `research/README.md`.
4. Resolve `{topic_slug}` from `research/context.json`.
5. Create or update the required artifact under `research/<topic_slug>/`.
6. Include every required heading exactly as specified.
7. Include one routing line: `Status: <allowed_status>`.
8. Choose the status honestly based on evidence.
9. Expect every stage gate to run semantic Markdown checklist checks, and key
   research gates to run deeper quality checklists.
10. Maintain evidence-control artifacts when the active stage requires them:
    `source_evidence_pack.csv`, `data_fitness_matrix.csv`,
    `claim_evidence_trace.csv`, `figure_blueprint.csv`,
    `figure_manifest.csv`, and `quality_report.md`.
11. Run or allow the Stop hook to run:

```bash
agent-harness step --task workflows/research.json --hook-json
```

If state is `choosing`, inspect options and choose:

```bash
agent-harness options --state .agent-harness/research-state.json
agent-harness choose <transition-id> --state .agent-harness/research-state.json --reason "<reason>"
```

If state is `waiting`, ask the user the required question, then use
`approve` or `reject` with a concrete reason.

The quality gates are intentionally stricter than format checks. If a checklist
blocks, repair the research logic rather than only editing prose.

Do not make unsupported claim-strength jumps. If the trace only supports a
mechanism claim, do not write causal, market-share, price, or supplier-selection
claims in the manuscript.

At `figures_manuscript`, generate real figure/table assets before setting
`Status: figures_synced`. Save them under `research/<topic_slug>/figures/`,
write `figure_manifest.csv`, and cite each asset ID/title/path in
`manuscript.md`. Prefer Python for data-derived visuals and computed tables.
Use imagegen only for conceptual mechanism visuals or graphical abstracts where
exact numeric fidelity is not required.

Do not edit workflow specs or checks during normal operation.
