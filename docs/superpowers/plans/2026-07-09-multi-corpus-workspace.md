# Multi-Corpus Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the single-corpus workspace into a monorepo of corpora — machinery at the root, each paper set under `corpora/<name>/`, one corpus selected per session before anything is read.

**Architecture:** The SessionStart hook lists corpus folder *names* only and prompts a selection; the agent writes the choice to a gitignored `.active-corpus` marker and scopes every path to `corpora/<active>/`. No reads before selection, no reads outside the active corpus, no cross-corpus operations. New-PDF detection moves entirely into `/sync`.

**Tech Stack:** Bash (SessionStart hook), Markdown agent-convention files (`CLAUDE.md`, `SKILL.md`, `README.md`), `.gitignore`, `.claude/settings.json`. No application code, no package manager.

## Global Constraints

- **Verification model — read this before every task.** This workspace has **no automated test suite**. Genuine verification per task is: `shellcheck` + fixture runs for the hook; `git check-ignore` for `.gitignore`; `grep` presence/consistency checks for the Markdown convention files; and one **live acceptance run** at the end (Task 7). Do **not** write assertion-free "tests" to satisfy a TDD template — that is a defect here, not compliance. Each task's verification steps below are the real gate.
- **Machinery stays corpus-agnostic.** `CLAUDE.md`, `.claude/skills/sync/SKILL.md`, the hook, and `README.md` must contain **no real corpus names** (no `floorplan`, `rplan`, `house-gan`, etc.). Use generic placeholders (`<name>`, `my-topic`). The concrete name `floorplan-generation` appears **only** in the Task 6 migration commands (which move the user's real local data) — never baked into a machinery file.
- **Never stage or commit the user's WIP.** The working tree carries uncommitted `.gitignore` lines (`synthesis/*`, `!synthesis/.gitkeep`) and untracked `synthesis/`, `.obsidian/`, and `.DS_Store` files. These are the user's and must be preserved, never `git add`ed. The Task 5 `.gitignore` edit must **keep** the `synthesis/` lines.
- **Path model:** define `C = corpora/<active-corpus>`, where `<active-corpus>` is the single line read from `.active-corpus`. Every corpus-relative path is under `C/`.
- **Marker file:** `.active-corpus` at the repo root holds exactly one line — the corpus folder name, nothing else.
- **Do not touch `.claude/settings.local.json`** (local/gitignored; its stale `detect-new-papers.sh` permission entries are harmless).
- **Every commit ends with these trailers:**
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011f9oNr7RXHeByYfACXjptt
  ```
- **Branch:** all work lands on `multi-corpus-workspace` (already checked out; the design spec is its first commit).

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `.claude/hooks/select-corpus.sh` | **rename** from `detect-new-papers.sh` + rewrite | List corpus names, prompt selection, read no file contents |
| `.claude/settings.json` | modify | Point the SessionStart hook at the new filename |
| `CLAUDE.md` | modify | Add corpus-selection section + hard rules; prefix routing paths with `corpora/<active>/` |
| `.claude/skills/sync/SKILL.md` | modify | Prefix all corpus paths with `C/`; add first-sync scaffolding; scope detection to the active corpus |
| `README.md` | modify | Describe the multi-corpus / select-on-start model |
| `.gitignore` | modify | Ignore `corpora/*` + `.active-corpus`; keep the user's `synthesis/` WIP lines |
| `corpora/.gitkeep` | **create** | Keep the empty corpora container in the template |
| `corpora/floorplan-generation/…` | **migrate (local)** | One-time move of the existing root corpus (gitignored data) |

Dependency order: Task 1 (hook) is independent. Tasks 2–4 (Markdown) are independent of each other. Task 5 (`.gitignore`) then Task 6 (migration) are adjacent to minimize the window where moved data is briefly untracked. Task 7 (acceptance) is last and needs everything in place.

---

### Task 1: SessionStart hook → corpus selector

**Files:**
- Rename + rewrite: `.claude/hooks/detect-new-papers.sh` → `.claude/hooks/select-corpus.sh`
- Modify: `.claude/settings.json`

**Interfaces:**
- Produces: a SessionStart context message listing `corpora/*` folder names + an instruction to ask the user which to open. Reads no file contents.
- Consumes: nothing from other tasks.

- [ ] **Step 1: Rename the hook, preserving history**

```bash
git mv .claude/hooks/detect-new-papers.sh .claude/hooks/select-corpus.sh
```

- [ ] **Step 2: Replace the hook body**

Overwrite `.claude/hooks/select-corpus.sh` with exactly:

```bash
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
```

- [ ] **Step 3: Ensure it stays executable**

```bash
chmod +x .claude/hooks/select-corpus.sh
```

- [ ] **Step 4: Update the hook registration**

In `.claude/settings.json`, change the command path from `detect-new-papers.sh` to `select-corpus.sh`. Result:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/select-corpus.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Lint the hook**

Run: `shellcheck .claude/hooks/select-corpus.sh`
Expected: no output (clean).

- [ ] **Step 6: Fixture run — two corpora**

```bash
D=$(mktemp -d); mkdir -p "$D/corpora/alpha" "$D/corpora/beta" "$D/corpora/alpha/papers"
CLAUDE_PROJECT_DIR="$D" bash .claude/hooks/select-corpus.sh
```
Expected: `AVAILABLE CORPORA (2):`, then ` - alpha` and ` - beta`, then the two instruction lines. (Order of alpha/beta may vary.)

- [ ] **Step 7: Fixture run — empty and missing `corpora/`**

```bash
D=$(mktemp -d); mkdir -p "$D/corpora"
CLAUDE_PROJECT_DIR="$D" bash .claude/hooks/select-corpus.sh   # expect "No corpora yet."
D2=$(mktemp -d)
CLAUDE_PROJECT_DIR="$D2" bash .claude/hooks/select-corpus.sh  # expect "No corpora/ directory found."
```
Expected: the empty case prints the "No corpora yet." block; the missing case prints the "No corpora/ directory found." block. Both exit 0.

- [ ] **Step 8: Commit**

```bash
git add .claude/hooks/select-corpus.sh .claude/settings.json
git commit -m "feat: SessionStart hook selects a corpus instead of detecting PDFs" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011f9oNr7RXHeByYfACXjptt"
```

---

### Task 2: `CLAUDE.md` — corpus selection + hard rules + scoped routing

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: the hook's behavior and the `.active-corpus` marker from Task 1.
- Produces: the behavioral contract every other task's wording must stay consistent with (path prefix `corpora/<active>/`, no cross-corpus, detection only in `/sync`).

- [ ] **Step 1: Rewrite the intro paragraph**

Find (exact):
> You are a research assistant grounded in the papers in this workspace. The corpus is the PDFs in `papers/`, with extracted text cached in `text/<slug>.md`, per-paper cards in `notes/<slug>.md`, machine metadata in `index.yaml`, and generated human views `INDEX.md` (overview table) and `LANDSCAPE.md` (corpus story + relation graph).

Replace with:
> You are a research assistant grounded in the papers in this workspace. Papers are organized into **corpora** — one folder per research area under `corpora/`. A session works on exactly one corpus, selected before anything is read (see "Working in a corpus" below). Within the active corpus `corpora/<active>/` (written `<active>/` below), the corpus is the PDFs in `<active>/papers/`, with extracted text cached in `<active>/text/<slug>.md`, per-paper cards in `<active>/notes/<slug>.md`, machine metadata in `<active>/index.yaml`, and generated human views `<active>/INDEX.md` (overview table) and `<active>/LANDSCAPE.md` (corpus story + relation graph).

- [ ] **Step 2: Insert the "Working in a corpus" section**

Immediately after the intro paragraph and before `## Answering questions: tiered routing`, insert:

```markdown
## Working in a corpus (select one first)

This workspace holds multiple corpora, each a folder under `corpora/<name>/` with its own `papers/`, `text/`, `notes/`, `_duplicates/`, `index.yaml`, `refs.yaml`, `INDEX.md`, and `LANDSCAPE.md`. **A session works on exactly one corpus, chosen before anything is read.**

- At session start, the `select-corpus.sh` hook lists the available corpus folder names. You MUST present them and ask the user which corpus to open. **Read or touch nothing until they answer** — no papers, no `index.yaml`, no cards, no grep.
- On their answer, validate it against the listed folders (on a mismatch, ask again — never create a corpus from a typo), write the bare name to `.active-corpus` at the repo root, and confirm "Active corpus: `<name>`."
- **After selection, every path is under `corpora/<active>/`** (written `<active>/` throughout this file). Reading, listing, or grepping anything outside the active corpus — another corpus, or the repo root — is forbidden.
- **One corpus per session.** There are no cross-corpus questions, comparisons, or operations. If asked one, say a session is scoped to a single corpus and offer to answer within the active one, or to restart for another.
- If your context is compacted mid-session, recover the active corpus by reading `.active-corpus`.
```

- [ ] **Step 3: Prefix the tiered-routing paths**

In `## Answering questions: tiered routing`, update the five tier bullets and the escalation bullet so their paths are corpus-scoped:
- Tier 0 `LANDSCAPE.md` → `<active>/LANDSCAPE.md`
- Tier 1 `index.yaml` → `<active>/index.yaml`
- Tier 2 `notes/<slug>.md` → `<active>/notes/<slug>.md`
- Tier 3 grep over `text/` → grep over `<active>/text/`
- Tier 4 full `text/<slug>.md` → full `<active>/text/<slug>.md`
- Escalation "each reading a share of `text/`" → "each reading a share of `<active>/text/`"

Also in the load-bearing rule, `text/<slug>.md` → `<active>/text/<slug>.md`.

- [ ] **Step 4: Prefix paths in "Grounding and citations" and "Ghost papers"**

- In "Grounding and citations", the "grep `text/`" phrase → "grep `<active>/text/`".
- In "Ghost papers", `refs.yaml` references → `<active>/refs.yaml` (the marker/citation syntax `⟨ghost:key⟩` is unchanged).

- [ ] **Step 5: Update the ingestion hook bullet**

Find (exact):
> - A SessionStart hook (`.claude/hooks/detect-new-papers.sh`) reports PDFs not yet in `index.yaml`. When it reports new papers, **ask the user** whether to ingest, then run the `sync` skill on confirmation. The hook never ingests.

Replace with:
> - A SessionStart hook (`.claude/hooks/select-corpus.sh`) lists the available corpora and asks you to open one; it reads no paper content and never ingests. New PDFs are detected inside the `sync` skill (Phase 1), scoped to the active corpus — when `/sync` reports new papers, ingest only on the user's confirmation.

- [ ] **Step 6: Prefix remaining file-discipline paths**

In "Ingestion and file discipline", scope the generated-file references: `INDEX.md`/`LANDSCAPE.md`/`refs.yaml`/`index.yaml`/`_duplicates/` mentions gain the `<active>/` prefix, and add at the end of the section: "All of the above paths are within the active corpus `corpora/<active>/`; nothing outside it is read or written."

- [ ] **Step 7: Consistency check**

```bash
grep -n "Working in a corpus" CLAUDE.md
grep -n "select-corpus.sh" CLAUDE.md
grep -n "<active>/" CLAUDE.md
grep -n "detect-new-papers" CLAUDE.md   # expect: no matches
grep -nE "cross-corpus|one corpus per session" CLAUDE.md
```
Expected: the section header, the hook name, several `<active>/` paths, the no-cross-corpus rule all present; zero remaining `detect-new-papers` references.

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: CLAUDE.md — corpus selection, hard scoping rules, per-corpus routing" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011f9oNr7RXHeByYfACXjptt"
```

---

### Task 3: `.claude/skills/sync/SKILL.md` — corpus-scoped paths + first-sync scaffolding

**Files:**
- Modify: `.claude/skills/sync/SKILL.md`

**Interfaces:**
- Consumes: `C = corpora/<active-corpus>` and the "detection only in /sync" contract from Task 2.
- Produces: the ingestion procedure scoped to one corpus, including scaffolding for a bare `mkdir`-created corpus.

- [ ] **Step 1: Add the active-corpus preamble**

Immediately after the `# /sync — corpus ingestion and regeneration` heading (before the "Incremental by design" paragraph), insert:

```markdown
**Active corpus.** `/sync` operates on exactly one corpus: the folder named in `.active-corpus`. Throughout this skill, `C` denotes `corpora/<active-corpus>/`. Every corpus path below — `papers/`, `text/`, `notes/`, `_duplicates/`, `index.yaml`, `refs.yaml`, `INDEX.md`, `LANDSCAPE.md` — lives under `C/`. If no corpus is selected yet, stop and ask the user to open one; never sync across corpora. (Temporary extraction to `/tmp` is not corpus-scoped.)
```

- [ ] **Step 2: Prefix corpus paths in Phases 1–5**

In the prose of Phases 1–5 and the Phase-2 dry-run table, apply this exact token mapping to the operative paths:

| bare | becomes |
|---|---|
| `papers/` | `C/papers/` |
| `text/` | `C/text/` |
| `notes/` | `C/notes/` |
| `_duplicates/` | `C/_duplicates/` |
| `index.yaml` | `C/index.yaml` |
| `refs.yaml` | `C/refs.yaml` |
| `INDEX.md` | `C/INDEX.md` |
| `LANDSCAPE.md` | `C/LANDSCAPE.md` |

Leave the `/tmp/<file>.txt` extraction target unchanged. Leave the illustrative code blocks under `## index.yaml entry schema`, `## refs.yaml entry schema (ghost tier)`, and `## Card template — notes/<slug>.md` as they are (they are schemas/templates, not operative paths), but update those three section *intro sentences* to note the file lives at `C/index.yaml`, `C/refs.yaml`, and `C/notes/<slug>.md` respectively.

- [ ] **Step 3: Add first-sync scaffolding to Phase 3**

At the top of `## Phase 3 — Execute`, before the numbered per-row steps, insert:

```markdown
**First sync of a new corpus:** if `C/` contains only `papers/` (no `C/index.yaml`), create the skeleton before ingesting — `C/text/`, `C/notes/`, `C/_duplicates/`, an empty `C/index.yaml`, and an empty `C/refs.yaml`. This is how a corpus created by a bare `mkdir corpora/<name>/papers` becomes live.
```

- [ ] **Step 4: Confirm the Phase-1 detection wording is corpus-scoped**

Ensure the Phase 1 "new iff its sha256 does not appear in `index.yaml`" and the orphan-detection sentence now read against `C/index.yaml`, `C/papers/`, and `C/_duplicates/` (covered by Step 2's mapping — verify no bare `index.yaml`/`papers/` remains in Phase 1).

- [ ] **Step 5: Consistency check**

```bash
grep -n "Active corpus" .claude/skills/sync/SKILL.md
grep -n "First sync of a new corpus" .claude/skills/sync/SKILL.md
# No bare operative corpus paths should remain in the phase prose. Inspect hits:
grep -nE '(^|[^/`])papers/|(^|[^/`])index\.yaml|(^|[^/`])text/|(^|[^/`])refs\.yaml' .claude/skills/sync/SKILL.md
```
Expected: preamble + scaffolding present. For the last grep, every remaining bare hit is inside a schema/template code block or the `## Card template — notes/<slug>.md` heading — not an operative Phase 1–5 instruction. Manually confirm each hit is illustrative, not operative.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/sync/SKILL.md
git commit -m "feat: /sync scoped to active corpus (C/ paths) + first-sync scaffolding" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011f9oNr7RXHeByYfACXjptt"
```

---

### Task 4: `README.md` — multi-corpus model

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the selection flow and layout from Tasks 1–3.
- Produces: user-facing docs; no downstream task depends on it.

- [ ] **Step 1: Add a corpora note after the opening**

After the "You have a folder of papers…" paragraph (before `## What it does`), insert:

```markdown
Papers are organized into **corpora** — one folder per research area under `corpora/`. Each session opens a single corpus; organizing, answering, and mapping are all scoped to it.
```

- [ ] **Step 2: Replace the Quickstart body**

Find the fenced `bash` block + the paragraph after it under `## Quickstart`. Replace the code block with:

```bash
git clone https://github.com/<you>/<your-repo>.git my-research && cd my-research
mkdir -p corpora/my-topic/papers
cp ~/Downloads/*.pdf corpora/my-topic/papers/
claude
```

And replace the paragraph after it with:

> Each research area is its own folder under `corpora/`. On session start, Claude lists your corpora and asks which one to open — a session works on exactly one. Run **`/sync`** to ingest: it shows a dry-run plan (renames + duplicate verdicts) for approval before touching any file, then extracts text, writes cards, and builds that corpus's index. After that, just ask questions — every answer is grounded in the open corpus.

Keep the "Or clone this repo directly to try it" line.

- [ ] **Step 3: Update "What stays local"**

Find (exact):
> Your PDFs and everything derived from them (`papers/`, `text/`, `notes/`, `_duplicates/`, `index.yaml`, `refs.yaml`, `INDEX.md`, `LANDSCAPE.md`) are gitignored. The repo carries only the machinery, so it can be reused on any set of papers.

Replace with:
> Everything under `corpora/` — each corpus's `papers/`, `text/`, `notes/`, `_duplicates/`, `index.yaml`, `refs.yaml`, `INDEX.md`, `LANDSCAPE.md` — plus the `.active-corpus` marker is gitignored. The repo carries only the machinery, so it can be reused for any number of paper sets.

- [ ] **Step 4: Presence check**

```bash
grep -n "corpora/" README.md
grep -n ".active-corpus" README.md
grep -n "lists your corpora" README.md
```
Expected: all present.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README — multi-corpus workspace, select-on-start flow" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011f9oNr7RXHeByYfACXjptt"
```

---

### Task 5: `.gitignore` + `corpora/.gitkeep`

**Files:**
- Modify: `.gitignore` (preserve the user's uncommitted `synthesis/` lines)
- Create: `corpora/.gitkeep`

**Interfaces:**
- Consumes: nothing.
- Produces: the ignore rules that keep migrated corpus data (Task 6) local.

- [ ] **Step 1: Read the current working-tree `.gitignore` first**

```bash
cat .gitignore
```
Note the user's uncommitted `synthesis/*` and `!synthesis/.gitkeep` lines — they MUST survive this edit.

- [ ] **Step 2: Rewrite the corpus-data section, keeping the synthesis WIP**

Replace the corpus-data block (the `papers/*`…`LANDSCAPE.md` lines) with `corpora/*` + `.active-corpus`, and **leave the `synthesis/*` / `!synthesis/.gitkeep` lines exactly as the user has them.** Target result (order of the synthesis lines may match wherever the user placed them):

```
# Corpus-derived content stays local — this repo is a replicable template.
corpora/*
!corpora/.gitkeep
.active-corpus

# user WIP (leave as-is)
synthesis/*
!synthesis/.gitkeep
```

Do not delete or reword the synthesis lines.

- [ ] **Step 3: Create the container keepfile**

```bash
mkdir -p corpora && touch corpora/.gitkeep
```

- [ ] **Step 4: Verify ignore behavior**

```bash
git check-ignore corpora/anything/papers/x.pdf corpora/anything/index.yaml .active-corpus   # all three should print (ignored)
git check-ignore corpora/.gitkeep && echo "BUG: .gitkeep ignored" || echo "ok: .gitkeep trackable"
git check-ignore synthesis/whatever && echo "ok: synthesis still ignored" || echo "BUG: synthesis WIP no longer ignored"
```
Expected: the three corpus paths are ignored; `corpora/.gitkeep` is **not** ignored; `synthesis/` still ignored.

- [ ] **Step 5: Stage ONLY `.gitignore` and the keepfile**

```bash
git add .gitignore corpora/.gitkeep
git status --short   # confirm synthesis/, .obsidian/, .DS_Store, docs/.DS_Store are NOT staged
```
If anything other than `.gitignore` and `corpora/.gitkeep` is staged, unstage it before committing.

- [ ] **Step 6: Commit**

```bash
git commit -m "chore: gitignore corpora/* and .active-corpus; add corpora/.gitkeep" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011f9oNr7RXHeByYfACXjptt"
```

---

### Task 6: Migrate the existing corpus (LOCAL, gitignored data)

> **Human-in-the-loop recommended.** This moves the user's real research data. Even under subagent-driven execution, run this task inline with the user aware, and dry-run the listing first. Nothing here is a tracked file change — it is a local `mv` of gitignored data — so there is no commit.

**Files:**
- Move (local): root `papers/ text/ notes/ _duplicates/ index.yaml refs.yaml INDEX.md LANDSCAPE.md` → `corpora/floorplan-generation/`

- [ ] **Step 1: Dry-run — show what exists and what will move**

```bash
ls -1 papers text notes index.yaml 2>/dev/null | head
echo "slug count (index entries):"; grep -c '^- slug:' index.yaml 2>/dev/null
```
Expected: the current root corpus is present; note the slug count for the after-check.

- [ ] **Step 2: Create the destination and move**

```bash
mkdir -p corpora/floorplan-generation
mv papers text notes _duplicates index.yaml refs.yaml INDEX.md LANDSCAPE.md corpora/floorplan-generation/ 2>/dev/null
```
(Any of the eight that does not exist is skipped by `2>/dev/null`; `papers/` and `index.yaml` must move.)

- [ ] **Step 3: Integrity check**

```bash
ls corpora/floorplan-generation/
echo "slug count after:"; grep -c '^- slug:' corpora/floorplan-generation/index.yaml
ls papers text notes index.yaml 2>/dev/null && echo "BUG: root corpus still present" || echo "ok: root corpus moved"
git status --short   # corpora/ data is ignored → should NOT appear; only pre-existing WIP shows
```
Expected: destination populated; slug count matches Step 1; no root corpus remains; `git status` shows no corpus data (it is ignored) and none of it is staged.

- [ ] **Step 4: No commit** — this task changes only gitignored local data. Proceed to Task 7.

---

### Task 7: Live acceptance run

> Interactive verification — run as a live session (controller or user), not an autonomous subagent. This is the real end-to-end test for the feature.

**Setup:** create a throwaway second corpus so cross-corpus and listing behavior can be exercised:

```bash
mkdir -p corpora/_acceptance/papers
cp corpora/floorplan-generation/papers/*.pdf corpora/_acceptance/papers/ 2>/dev/null | head   # any one PDF is enough; or drop a small test PDF
```

- [ ] **1. Pre-selection silence.** Start a fresh session. Confirm the hook lists exactly `floorplan-generation` and `_acceptance` (names only) and that no corpus file is read before you answer.
- [ ] **2. Selection + marker.** Open `floorplan-generation`. Confirm `.active-corpus` contains `floorplan-generation` and the agent reports the active corpus.
- [ ] **3. Scoped grounding.** Ask a real question. Confirm the answer is grounded only in the active corpus and citations resolve under `corpora/floorplan-generation/text/`.
- [ ] **4. Firewall.** Ask a cross-corpus question ("compare this to my other corpus"). Confirm refusal + offer to stay within the active corpus.
- [ ] **5. Scoped sync.** Run `/sync`. Confirm it reads/writes only under `corpora/floorplan-generation/` and detects only that corpus's new PDFs (expect none new).
- [ ] **6. New-corpus scaffolding.** In a fresh session, open `_acceptance` and `/sync`. Confirm the skeleton (`text/`, `notes/`, `index.yaml`, …) is scaffolded and the PDF ingests.
- [ ] **7. Compaction recovery.** Confirm that after a mid-session compaction the agent continues on the same corpus via `.active-corpus` (observe on the next natural compaction, or reason through it).
- [ ] **8. Cleanup.** `rm -rf corpora/_acceptance` (throwaway; gitignored).

After acceptance passes, proceed to the whole-branch review and `superpowers:finishing-a-development-branch`.

---

## Self-Review notes (author)

- **Spec coverage:** layout (Task 5/6), `.active-corpus` (Tasks 1–2, 5), lifecycle (Tasks 1–2), hard rules (Task 2), `/sync` changes (Task 3), hook (Task 1), `.gitignore` (Task 5), migration (Task 6), acceptance (Task 7) — all mapped.
- **No fake tests:** verification is shell/`grep`/`git check-ignore`/live run, matching the project's established practice; the Global Constraints call this out so reviewers do not flag honest presence-checks as inadequate.
- **WIP safety:** the `synthesis/` preservation and "never `git add` WIP" constraint is stated globally and re-checked in Tasks 5–6.
- **Type/name consistency:** `C = corpora/<active-corpus>` and `<active>/` are used consistently across Tasks 2–3; the real name `floorplan-generation` is confined to Task 6.
