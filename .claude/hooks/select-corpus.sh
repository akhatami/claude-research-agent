#!/bin/bash
# SessionStart hook: list available corpora (folder names under corpora/) and
# instruct the agent to ask the user which one to open. Reads NO file contents —
# names only. Corpus selection and all ingestion are agent work (see /sync).
set -u
cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}" || exit 0

if [ ! -d corpora ]; then
  echo "No corpora/ directory found. Create a corpus with:"
  echo "  mkdir -p corpora/<name>/papers  &&  cp *.pdf corpora/<name>/papers/"
  echo "then restart the session."
  exit 0
fi

names=()
for d in corpora/*/; do
  [ -d "$d" ] || continue
  names+=("$(basename "$d")")
done

if [ ${#names[@]} -eq 0 ]; then
  echo "No corpora yet. Create one with:"
  echo "  mkdir -p corpora/<name>/papers  &&  cp *.pdf corpora/<name>/papers/"
  echo "then restart the session."
  exit 0
fi

echo "AVAILABLE CORPORA (${#names[@]}):"
printf ' - %s\n' "${names[@]}"
echo "Ask the user which corpus to open. Read or touch NOTHING until they answer."
echo "On their answer: write the bare corpus name to .active-corpus and scope all work to corpora/<that-name>/."
exit 0
