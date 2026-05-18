# Agent Harness Research Workflow Instructions

This repository contains one example only: a research workflow driven by
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

- Workflow spec: `workflows/research.json`
- Artifact contract: `research/README.md`
- Runtime context: `research/context.json`
- State path: `.agent-harness/research-state.json`
- Report directory: `reports/research`
- Stop hook: `.codex/hooks/run-agent-harness-check.sh`
- Project skill: `.agents/skills/research-workflow-runner/SKILL.md`

If workflow state exists, continue from the current active node. If no state
exists, start at `research_context`.

At `research_context`, create `research/context.json` and the topic directory
under `research/<topic_slug>/`. Use a stable lower-kebab ASCII slug derived from
the user's research idea. Example:

```json
{
  "topic_title": "AI-generated search summaries and source diversity",
  "topic_slug": "ai-search-source-diversity",
  "research_dir": "research/ai-search-source-diversity"
}
```

## How To Work A Node

For each active workflow node:

1. Read the node's artifact contract in `research/README.md`.
2. Read `research/context.json` to resolve `{topic_slug}`.
3. Create or update the required artifact under `research/<topic_slug>/`.
4. Include every required heading exactly as specified.
5. Include one routing line: `Status: <allowed_status>`.
6. Choose the status honestly from the node's allowed statuses based on the
   current research evidence.
7. Do not advance by optimism. If evidence is weak, incomplete, blocked, or
   already known, use the status that routes back for repair.

The workflow has four gate layers:

- structure: artifact exists, required headings are present, and minimum
  substantive length is met;
- stage semantics: Markdown checklist judge verifies the stage is genuinely
  complete and the status is justified;
- deep quality: critical gates check research-object modeling, true information
  delta, method-claim match, data provenance, evidence boundaries, alternative
  explanations, generated figure/table quality, publication-style prose, and
  manuscript argument carrying capacity.
- evidence controls: deterministic CSV and link checks require source evidence
  packs, data fitness matrices, claim-evidence traces, calibrated claim
  strength, generated visual assets, reader-facing citations/references, and a
  final aggregate quality report.

Key evidence-control artifacts:

- `source_evidence_pack.csv`: source IDs, authority level, locator/excerpt,
  extracted fact, uncertainty, and used-in-claim mapping.
- `data_fitness_matrix.csv`: claim/data fit, directness, what the data cannot
  support, distortion risk, mitigation, and routing decision.
- `claim_evidence_trace.csv`: claim IDs, claim strength, source IDs,
  method support, evidence boundary, falsification test, and negative evidence.
- `figure_blueprint.csv`: planned figure/table assets, generation methods,
  claim IDs, source IDs, planned paths, and caption stubs.
- `figure_manifest.csv`: generated figure/table assets, file paths, generation
  methods, claim IDs, source IDs, captions, and publication status.
- `quality_report.md`: final stage outcomes, failed gates and repairs, claim
  coverage, data/source audit, residual risks, and external-use readiness.

For `figures_manuscript`, do not stop at a `Figure Plan`. Generate actual
assets under `research/<topic_slug>/figures/`, write `figure_manifest.csv`, and
reference each asset from `manuscript.md`. Use Python for data-derived visuals
and computed tables; use `imagegen` only for conceptual mechanism visuals or
graphical abstracts where numeric fidelity is not required.

The manuscript's main reader-facing sections (`Abstract`, `Introduction`,
`Methods`, `Results`, `Discussion`, `Conclusion`) must not leak harness
mechanics. Do not mention workflow, checks, checklist files, local paths,
`source_evidence_pack.csv`, `claim_evidence_trace.csv`,
`data_fitness_matrix.csv`, `figure_manifest.csv`, internal source IDs, internal
claim IDs, or figure asset IDs in those sections. Put file paths and manifest
details only in `Figures and Tables`, use reader-facing citations in the body,
and add `References`.

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
agent-harness validate-workflow --task workflows/research.json
agent-harness step --task workflows/research.json --hook-json
agent-harness status --state .agent-harness/research-state.json
agent-harness options --state .agent-harness/research-state.json
agent-harness choose <transition-id> --state .agent-harness/research-state.json --reason "<reason>"
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
- `research/context.json`
- `research/<topic_slug>/`
