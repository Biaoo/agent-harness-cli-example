---
name: harness-workflow-runner
description: Use when running this repository's AI-IE Agent Harness workflow from a user research idea, producing active-node artifacts, handling step/options/choose/approve/reject, and continuing until research_complete.
---

# Harness Workflow Runner

This repository has one workflow:

- Workflow spec: `workflows/ai-ie-research.json`
- Artifact contract: `research/ai-ie/README.md`
- State path: `.agent-harness/ai-ie-research-state.json`
- Report directory: `reports/research-workflow`

Users should be able to start with a short prompt:

```text
Research this idea with the AI-IE research workflow:

<idea>
```

Read `AGENTS.md` first. It is the project source of truth for how to operate the
workflow.

## Operating Loop

1. If state exists, continue from the active node. If no state exists, start at
   `idea_intake`.
2. Read the active node's artifact contract in `research/ai-ie/README.md`.
3. Create or update the required Markdown artifact under `research/ai-ie/`.
4. Include every required heading exactly as specified.
5. Include one routing line: `Status: <allowed_status>`.
6. Choose the status honestly based on evidence.
7. Run or allow the Stop hook to run:

```bash
agent-harness step --task workflows/ai-ie-research.json --hook-json
```

If state is `choosing`, inspect options and choose:

```bash
agent-harness options --state .agent-harness/ai-ie-research-state.json
agent-harness choose <transition-id> --state .agent-harness/ai-ie-research-state.json --reason "<reason>"
```

If state is `waiting`, ask the user the required question, then use
`approve` or `reject` with a concrete reason.

Do not edit workflow specs or checks during normal operation.
