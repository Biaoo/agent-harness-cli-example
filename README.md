# Agent Harness CLI Example

This workspace demonstrates using project-level Codex hooks to validate a
generated argumentative essay with `agent-harness`.

Start a Codex session in this directory and ask:

```text
Write an argumentative essay about "preserving deep thinking in the age of efficiency".
Save it to essay.md. The essay must be 1000 characters, with an allowed deviation of no more than 10 characters.
```

The project-level Stop hook in `.codex/hooks.json` runs:

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness run-checks --task task.json --report-id latest
```

The hook uses the published PyPI package directly. It only assumes `uv` is
available on `PATH`; it does not depend on a sibling checkout or editable local
install.

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness --help
```

The hook writes reports under `reports/`. To inspect the latest report:

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness view latest --page-size 2
```

If a blocking check fails, the Stop hook returns a Codex continuation decision
instead of allowing the turn to finish. Codex should use the generated report,
revise the artifact, rerun the harness, and finish only after blocking checks
pass.

The task includes one deterministic length check and one local Codex content
check. All content requirements live in `checklists/essay_quality.md`; `task.json`
only points to the artifact, check script, and checklist path. The check script
owns its local Codex call through `checks/local_codex_judge.py`, asks Codex to
fill the Markdown checklist, then parses `- [x]` and `- [ ]` into the harness
report. This avoids making Codex produce strict JSON directly.

The hook enables the LLM checklist checks by default. To run only deterministic
checks manually:

```bash
AGENT_HARNESS_ENABLE_LLM=0 uvx --from agent-harness-cli==0.1.1 agent-harness run-checks --task task.json --report-id deterministic
```
