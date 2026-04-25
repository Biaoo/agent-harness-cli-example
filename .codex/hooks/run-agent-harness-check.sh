#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${ROOT}/reports"
REPORT_ID="latest"
HARNESS_PACKAGE="agent-harness-cli==0.1.1"
mkdir -p "${LOG_DIR}"

cd "${ROOT}"

if [[ "${AGENT_HARNESS_HOOK_ACTIVE:-}" == "1" ]]; then
  exit 0
fi
export AGENT_HARNESS_HOOK_ACTIVE=1

if ! command -v uv >/dev/null 2>&1; then
  python3 - <<'PY'
import json

message = (
    "uv was not found on PATH. Install uv first, then this hook can run "
    "the published agent-harness-cli package with uvx."
)
print(json.dumps({
    "systemMessage": message,
}, ensure_ascii=False))
PY
  exit 0
fi

set +e
AGENT_HARNESS_ENABLE_LLM="${AGENT_HARNESS_ENABLE_LLM:-1}" \
  uvx --from "${HARNESS_PACKAGE}" agent-harness run-checks \
    --task task.json \
    --report-id "${REPORT_ID}" \
    --timeout 300 \
    > "${LOG_DIR}/${REPORT_ID}.summary.txt" 2>&1
status=$?
set -e

HARNESS_STATUS="${status}" \
LOG_DIR="${LOG_DIR}" \
REPORT_ID="${REPORT_ID}" \
HARNESS_PACKAGE="${HARNESS_PACKAGE}" \
python3 - <<'PY'
import json
import os
from pathlib import Path

status = int(os.environ["HARNESS_STATUS"])
log_dir = Path(os.environ["LOG_DIR"])
report_id = os.environ["REPORT_ID"]
harness_package = os.environ["HARNESS_PACKAGE"]
summary = (log_dir / f"{report_id}.summary.txt").read_text(encoding="utf-8")
report_path = log_dir / f"{report_id}.json"
view_command = f"uvx --from {harness_package} agent-harness view {report_id} --failed-only --page-size 5"

if status == 0:
    raise SystemExit(0)

failed_lines = []
if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for check in report.get("checks", []):
        if check.get("passed", False):
            continue
        failed_lines.append(
            f"- {check.get('check', 'unknown_check')}: "
            f"{check.get('summary', 'No summary returned.')} "
            f"(severity={check.get('severity', 'error')})"
        )
        for reason in check.get("reasons", [])[:2]:
            if not isinstance(reason, dict):
                continue
            message = reason.get("message")
            suggestion = reason.get("suggestion")
            if message:
                failed_lines.append(f"  Reason: {message}")
            if suggestion:
                failed_lines.append(f"  Suggestion: {suggestion}")
else:
    failed_lines.append(summary.strip() or f"agent-harness exited with status {status}.")

reason = "\n".join([
    "Agent harness found blocking failures, so do not finalize this turn yet.",
    "Use the report below, update the artifact, then rerun the harness. Finish only after the blocking checks pass.",
    "",
    f"Report: reports/{report_id}.json",
    f"View failed checks: {view_command}",
    "",
    "Failed checks:",
    "\n".join(failed_lines),
])

print(json.dumps({
    "decision": "block",
    "reason": reason,
}, ensure_ascii=False))
PY

exit 0
