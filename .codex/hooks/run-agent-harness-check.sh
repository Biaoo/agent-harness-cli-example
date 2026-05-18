#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKFLOW_PATH="workflows/ai-ie-research.json"
REPORT_ID="research-latest"
LOG_DIR="${ROOT}/reports/research-workflow"
STDOUT_PATH="${LOG_DIR}/${REPORT_ID}.hook.json"
STDERR_PATH="${LOG_DIR}/${REPORT_ID}.stderr.txt"
HARNESS_PACKAGE="agent-harness-cli==0.1.2"
mkdir -p "${LOG_DIR}"

cd "${ROOT}"

if [[ "${AGENT_HARNESS_HOOK_ACTIVE:-}" == "1" ]]; then
  exit 0
fi
export AGENT_HARNESS_HOOK_ACTIVE=1

if command -v agent-harness >/dev/null 2>&1; then
  HARNESS_CMD=(agent-harness)
elif command -v uv >/dev/null 2>&1; then
  HARNESS_CMD=(uvx --from "${HARNESS_PACKAGE}" agent-harness)
else
  python3 - <<'PY'
import json

print(json.dumps({
    "systemMessage": (
        "No agent-harness command was found and uv is unavailable. "
        "Install uv or install agent-harness-cli==0.1.2."
    )
}, ensure_ascii=False))
PY
  exit 0
fi

set +e
"${HARNESS_CMD[@]}" step \
  --task "${WORKFLOW_PATH}" \
  --report-id "${REPORT_ID}" \
  --timeout 300 \
  --hook-json \
  > "${STDOUT_PATH}" 2> "${STDERR_PATH}"
status=$?
set -e

HARNESS_STATUS="${status}" \
STDOUT_PATH="${STDOUT_PATH}" \
STDERR_PATH="${STDERR_PATH}" \
WORKFLOW_PATH="${WORKFLOW_PATH}" \
REPORT_ID="${REPORT_ID}" \
python3 - <<'PY'
import json
import os
from pathlib import Path

status = int(os.environ["HARNESS_STATUS"])
stdout_path = Path(os.environ["STDOUT_PATH"])
stderr_path = Path(os.environ["STDERR_PATH"])
workflow_path = os.environ["WORKFLOW_PATH"]
report_id = os.environ["REPORT_ID"]
stdout = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""

try:
    payload = json.loads(stdout)
except json.JSONDecodeError:
    payload = None

if isinstance(payload, dict) and ("decision" in payload or "systemMessage" in payload):
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0)

reason = "\n".join([
    "Agent harness workflow hook could not read a valid hook JSON payload.",
    f"Workflow: {workflow_path}",
    f"Report id: {report_id}",
    f"Exit status: {status}",
    "",
    "stdout tail:",
    stdout[-2000:] or "<empty>",
    "",
    "stderr tail:",
    stderr[-2000:] or "<empty>",
])

print(json.dumps({
    "decision": "block",
    "reason": reason,
}, ensure_ascii=False))
PY

exit 0
