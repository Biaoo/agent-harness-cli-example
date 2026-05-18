# Agent Harness Research Workflow Instructions

This repository contains one example only: an AI-IE research workflow driven by
`agent-harness` workflow-controller commands.

Use only the workflow-controller path described below.

## Default User Interaction

The user should only need to provide a research task or idea, for example:

```text
Research this idea: <idea>
```

When the user provides an idea, do not ask them to restate harness mechanics.
Use this repository's workflow contract automatically.

## Workflow Source of Truth

- Workflow spec: `workflows/ai-ie-research.json`
- Artifact contract: `research/ai-ie/README.md`
- State path: `.agent-harness/ai-ie-research-state.json`
- Report directory: `reports/research-workflow`
- Stop hook: `.codex/hooks/run-agent-harness-check.sh`
- Project skill: `.agents/skills/harness-workflow-runner/SKILL.md`

If workflow state exists, continue from the current active node. If no state
exists, start at `idea_intake`.

## How To Work A Node

For each active workflow node:

1. Read the node's artifact contract in `research/ai-ie/README.md`.
2. Create or update the required Markdown artifact under `research/ai-ie/`.
3. Include every required heading exactly as specified.
4. Include one routing line: `Status: <allowed_status>`.
5. Choose the status honestly from the node's allowed statuses based on the
   current research evidence.
6. Do not advance by optimism. If evidence is weak, incomplete, blocked, or
   already known, use the status that routes back for repair.

The workflow has three gate layers:

- structure: artifact exists, required headings are present, and minimum
  substantive length is met;
- stage semantics: Markdown checklist judge verifies the stage is genuinely
  complete and the status is justified;
- deep quality: critical gates check research-object modeling, true information
  delta, method-claim match, data provenance, evidence boundaries, alternative
  explanations, and manuscript argument carrying capacity.

Content quality checks use local `codex exec` to fill Markdown checklists, then
the check script parses the checklist into harness JSON. For deterministic-only
debugging, set `AGENT_HARNESS_ENABLE_LLM=0`; do not use that setting for normal
research validation.

The research rule is strict:

```text
Either produce a main-text-level insight, or loop back for repair.
Do not route to SI-only digestion, downgrade publication, or a weaker fallback paper.
```

## Harness Commands

Use the published CLI:

```bash
uv tool install agent-harness-cli==0.1.2
agent-harness validate-workflow --task workflows/ai-ie-research.json
agent-harness step --task workflows/ai-ie-research.json --hook-json
agent-harness status --state .agent-harness/ai-ie-research-state.json
agent-harness options --state .agent-harness/ai-ie-research-state.json
agent-harness choose <transition-id> --state .agent-harness/ai-ie-research-state.json --reason "<reason>"
```

When a node appears ready, it is acceptable to stop normally and let the Stop
hook run `agent-harness step`. If you are working manually, run the `step`
command yourself.

If the workflow enters `choosing`, inspect the available options before choosing.
Use the transition that best matches the evidence and include a concrete reason.

## Generated Files

Do not commit runtime state or reports:

- `.agent-harness/`
- `reports/`
