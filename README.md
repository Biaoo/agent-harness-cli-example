# Agent Harness CLI Example

[English](README.md) | [简体中文](README.zh-CN.md)

A minimal Codex writing task using the `agent-harness-cli` reference pattern.

This repository is a runnable example for
[Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli). It shows
how the practical reference framework applies to an agentic writing task:
Codex writes an argumentative essay, project-level hooks run checks, and the
report guides the next agent pass.

## Harness Engineering Flow

The example uses writing a short essay as the artifact, but the important part
is the acceptance loop around that artifact:

1. Codex writes `essay.md`.
2. A project-level Stop hook runs `agent-harness`.
3. The harness runs deterministic and LLM-assisted checks.
4. Blocking failures are returned to Codex as a continuation prompt.
5. Codex revises the artifact and reruns the loop until blocking checks pass.

This demonstrates the artifact-focused role of harness engineering in agentic
work: make the target constrained, observable, and verifiable; externalize
acceptance criteria; and let the agent iterate against evidence.

The same pattern applies to project documents, specifications, research notes,
code changes, data reports, and other artifacts that benefit from agent-friendly
checks.

The example keeps the same boundary as the CLI: the framework supplies the loop,
while the project owns the artifact contract, checklist, check scripts, and LLM
judge behavior.

## What To Learn From This Example

- The artifact contract is explicit: Codex must write `essay.md`.
- Objective requirements become deterministic checks, such as exact length.
- Semantic requirements live in a human-readable checklist.
- The LLM judge fills the checklist instead of producing final harness JSON.
- The check script parses the checklist into deterministic harness output.
- A failed blocking check becomes Codex's next prompt through the Stop hook.

## Related Projects

- CLI and skill source: [Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli)
- This repository demonstrates the published `agent-harness-cli` package and
  the Codex Stop hook workflow.

## Acceptance Surface

The task asks Codex to write an argumentative essay about preserving deep
thinking in the age of efficiency.

The harness runs two checks:

| Requirement | Check | Type | Severity | Source of truth |
| --- | --- | --- | --- | --- |
| The essay is 1000 characters plus or minus 10. | `essay_length` | deterministic script | `error` | `task.json` length config |
| The essay satisfies the argument-quality rubric. | `essay_quality` | local Codex checklist judge | `warning` | `checklists/essay_quality.md` |

Content requirements live in the Markdown checklist. The LLM judge fills the
checklist, and the check script parses `- [x]` and `- [ ]` into harness JSON.
This keeps the final machine contract deterministic without forcing the model to
produce strict JSON directly.

## Prerequisites

| Tool | Required version | Why it is needed | Verify |
| --- | --- | --- | --- |
| `uv` | `0.9.3` | Runs the published `agent-harness-cli` package through `uvx`. | `uv --version` |
| `agent-harness-cli` | `0.1.1` | Provides `agent-harness run-checks` and `agent-harness view`. | The hook pins `uvx --from agent-harness-cli==0.1.1 ...`; no global install is required. |
| Codex CLI | `codex-cli 0.125.0` | Runs the local LLM checklist judge through `codex exec`. | `codex --version` |

If Codex CLI is installed through npm:

```bash
npm install -g @openai/codex@0.125.0
```

The quality checklist check calls `codex exec`, so Codex CLI must also be logged
in and usable non-interactively in this directory. This example was verified with
Node.js `v22.22.2` and npm `10.9.7`.

## Try It

Start a Codex session in this directory and ask:

```text
Write an argumentative essay about "preserving deep thinking in the age of efficiency".
Save it to essay.md. The essay must be 1000 characters, with an allowed deviation of no more than 10 characters.
```

When Codex attempts to stop, the project-level Stop hook in `.codex/hooks.json`
runs:

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness run-checks --task task.json --report-id latest
```

If a blocking check fails, the hook returns a Codex continuation decision instead
of allowing the turn to finish. Codex should use the generated report, revise the
artifact, rerun the harness, and finish only after blocking checks pass.

## Inspect Reports

Reports are written under `reports/`.

View the latest report:

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness view latest --page-size 2
```

View only failed checks:

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness view latest --failed-only --page-size 5
```

Run only deterministic checks manually:

```bash
AGENT_HARNESS_ENABLE_LLM=0 uvx --from agent-harness-cli==0.1.1 agent-harness run-checks --task task.json --report-id deterministic
```

## Project Layout

```text
.codex/
  hooks.json                         Project-level Stop hook config.
  hooks/run-agent-harness-check.sh   Hook script that runs the harness.
checklists/
  essay_quality.md                   Human-readable content checklist.
checks/
  check_length.py                    Deterministic length check.
  check_llm_content.py               Checklist-based content check.
  local_codex_judge.py               Local codex exec helper owned by this example.
task.json                            Harness task definition.
essay.md                             Generated artifact, created by Codex during the task.
```

## Design Notes

- The example uses the published PyPI package directly with `uvx`.
- There is no sibling checkout or editable local dependency.
- The Stop hook uses `decision: "block"` for blocking failures so Codex keeps
  working.
- LLM-specific logic lives in the example's own check script, not in the CLI.
- `reports/` is generated output and should not be committed.
