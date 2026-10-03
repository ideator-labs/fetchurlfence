#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"

LOG="$ROOT/data/fetches.log"
mkdir -p "$ROOT/data"
: > "$LOG"

pass_count=0
fail_count=0

echo "=== FetchUrlFence demo ==="
echo "Application-layer URL/IP fence for MCP-style fetch tools."
echo "No real network egress; redirect hops are fixtures."
echo

# PATH A: unguarded accepts cloud metadata URL
echo "PATH A (unguarded metadata): BEFORE lines=0"
a_out=$(python3 - <<'PY'
from pathlib import Path
from fetch_tool import FetchTool, clear_log, log_lines
log = Path("data/fetches.log")
clear_log(log)
tool = FetchTool(log, fenced=False)
r = tool.fetch("http://169.254.169.254/latest/meta-data/")
lines = log_lines(log)
print(f"ok={r['ok']} reason={r['reason']} fetched={r['fetched']} lines={len(lines)}")
PY
)
echo "PATH A AFTER=$a_out"
if [[ "$a_out" == "ok=True reason=open fetched=http://169.254.169.254/latest/meta-data/ lines=1" ]]; then
  echo "PATH A (unguarded metadata): PASS"
  pass_count=$((pass_count + 1))
else
  echo "PATH A (unguarded metadata): FAIL"
  fail_count=$((fail_count + 1))
fi
echo

# PATH B: fenced rejects the same metadata URL
echo "PATH B (fenced metadata): BEFORE lines=0"
b_out=$(python3 - <<'PY'
from pathlib import Path
from fetch_tool import FetchTool, clear_log, log_lines
log = Path("data/fetches.log")
clear_log(log)
tool = FetchTool(log, fenced=True)
r = tool.fetch("http://169.254.169.254/latest/meta-data/")
lines = log_lines(log)
print(f"ok={r['ok']} reason={r['reason']} fetched={r['fetched']} lines={len(lines)}")
PY
)
echo "PATH B AFTER=$b_out"
if [[ "$b_out" == "ok=False reason=blocked_metadata fetched=None lines=0" ]]; then
  echo "PATH B (fenced metadata): PASS"
  pass_count=$((pass_count + 1))
else
  echo "PATH B (fenced metadata): FAIL"
  fail_count=$((fail_count + 1))
fi
echo

# PATH C: fenced rejects redirect hop to private IP
echo "PATH C (fenced redirect-to-private): BEFORE lines=0"
c_out=$(python3 - <<'PY'
from pathlib import Path
from fetch_tool import FetchTool, clear_log, log_lines
log = Path("data/fetches.log")
clear_log(log)
tool = FetchTool(log, fenced=True)
r = tool.fetch("http://8.8.8.8/redir")
lines = log_lines(log)
print(f"ok={r['ok']} reason={r['reason']} blocked={r.get('blocked_url')} lines={len(lines)}")
PY
)
echo "PATH C AFTER=$c_out"
if [[ "$c_out" == "ok=False reason=blocked_redirect_hop blocked=http://10.0.0.5/secret lines=0" ]]; then
  echo "PATH C (fenced redirect-to-private): PASS"
  pass_count=$((pass_count + 1))
else
  echo "PATH C (fenced redirect-to-private): FAIL"
  fail_count=$((fail_count + 1))
fi
echo

echo "SUMMARY: $pass_count passed, $fail_count failed"
if [[ "$fail_count" -ne 0 || "$pass_count" -ne 3 ]]; then
  exit 1
fi
echo "ALL CLAIMS PASSED"
exit 0
