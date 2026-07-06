#!/bin/bash
# SessionStart hook: report PDFs in papers/ whose sha256 is not recorded in
# index.yaml. Detection only — ingestion is agent work, run via /sync.
set -u
cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}" || exit 0
[ -d papers ] || exit 0

new_files=()
for f in papers/*.pdf; do
  [ -e "$f" ] || continue
  hash=$(shasum -a 256 "$f" | awk '{print $1}')
  if ! grep -q "$hash" index.yaml 2>/dev/null; then
    new_files+=("$f")
  fi
done

if [ ${#new_files[@]} -gt 0 ]; then
  echo "NEW PAPERS DETECTED: ${#new_files[@]} PDF(s) in papers/ are not in index.yaml:"
  printf ' - %s\n' "${new_files[@]}"
  echo "Ask the user whether to ingest them now with the sync skill. Do not ingest without asking."
fi
exit 0
