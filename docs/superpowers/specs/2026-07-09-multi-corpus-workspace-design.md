# Multi-Corpus Workspace — Design

**Date:** 2026-07-09
**Status:** Awaiting user approval
**Extends:** [2026-07-06-research-assistant-workspace-design.md](2026-07-06-research-assistant-workspace-design.md)

## What this is

Today the workspace is single-tenant: one corpus lives at the repo root (`papers/`, `text/`, `notes/`, `index.yaml`, …), and running the machinery against a different set of papers means cloning the template again. Machinery improvements do not propagate to existing clones, and juggling several research areas means several checkouts.

This turns the workspace **multi-tenant** by restructuring it as a **monorepo of corpora**: the machinery lives once at the root, and each set of papers is a subfolder under `corpora/` that carries its own generated artifacts. One session works on exactly one corpus, chosen at session start. Machinery edits are made once and apply to every corpus.

**Scope target:** a single operator running several independent research corpora from one checkout. Explicitly *not* in scope: cross-corpus questions, mid-session corpus switching, or concurrent sessions on different corpora in the same checkout.

## Core principle: one corpus per session, chosen before anything is read

The workspace's load-bearing rule remains **cards and index may *route*; only full text may *ground*.** This design adds a second boundary in front of it:

> **Nothing is read until a corpus is selected, and after selection nothing outside that corpus is ever read.**

The active corpus is a hard, session-long scope. There is no cross-corpus operation. This keeps the grounding firewall clean: every answer is grounded in exactly one corpus, and a citation always resolves inside `corpora/<active>/`.

## Layout

```
research/
  CLAUDE.md                        ← shared machinery (tracked)
  .claude/skills/sync/SKILL.md     ← shared
  .claude/hooks/select-corpus.sh   ← shared
  docs/                            ← shared design docs
  .active-corpus                   ← session state (gitignored)
  corpora/
    <name-A>/
      papers/  text/  notes/  _duplicates/
      index.yaml  refs.yaml  INDEX.md  LANDSCAPE.md
    <name-B>/
      papers/  …
```

The machinery at the root is identical for every corpus. Everything under `corpora/<name>/` mirrors exactly today's single-corpus layout, one level deeper.

## Active-corpus state — `.active-corpus`

A single-line plain-text file at the repo root holding the selected corpus folder name (e.g. `floorplan-generation`). Gitignored — it is session state, not machinery.

- **Written** by the agent immediately after the user names a corpus, never by the hook.
- **Purpose:** recovery. If the agent's context is compacted mid-session, it re-reads `.active-corpus` to recover the active scope rather than re-asking.
- **Not authoritative at session start.** Every session re-asks (see lifecycle); a marker left from a prior session is overwritten by this session's selection before any corpus work, and is never trusted before the user has answered this session.
- **Single active corpus per checkout.** Concurrent sessions on different corpora in the same checkout are out of scope; the last selection wins.

## Session lifecycle

1. **Session start.** The `select-corpus.sh` SessionStart hook runs a bare directory listing of `corpora/` — folder **names only**, reading nothing inside them (no papers, no `index.yaml`, no cards). It emits the names plus an instruction: *"Ask the user which corpus to work on. Do not read or touch any file until they answer."*
   - If `corpora/` is empty, the hook instead instructs the agent to tell the user to create a corpus (`mkdir corpora/<name>/papers`, add PDFs) and restart.
2. **Prompt.** The agent presents the names and asks the user to pick one. It performs no other action — no reads, no scans.
3. **Selection.** The user names a corpus. The agent validates it against the listed folders (on typo/no-match, re-ask — never create), writes the name to `.active-corpus`, and confirms: *"Active corpus: `<name>`."*
4. **Scoped operation.** From here every path is under `corpora/<name>/`. Questions route through the existing tiers within that corpus; `/sync` operates on that corpus; new PDFs are detected only inside `/sync`.
5. **Compaction recovery.** If context is compacted, the agent recovers the active corpus from `.active-corpus`.
6. **Switching = new session.** To work on a different corpus, the user starts a new session, which re-asks. The corpus is fixed for the life of a session.

## Hard rules (added to `CLAUDE.md`)

1. **No file access before selection.** The only permitted pre-selection action is presenting the hook's name list and asking the user to choose. No reads of any kind until `.active-corpus` is set this session.
2. **After selection, every path is `corpora/<active>/…`.** Reading, listing, or grepping anything outside the active corpus is forbidden — including other corpora and the root.
3. **No cross-corpus questions, comparisons, or operations — ever.** If asked, the agent states that a session is scoped to one corpus and offers to answer within the active one (or to restart for another).
4. **Tiered routing is unchanged, scoped to the corpus.** LANDSCAPE → index → cards → text, still lazy: never eager-load a whole corpus.
5. **New PDFs are discovered only during `/sync`.** There is no proactive scan on selection or at session start.

## `/sync` changes

The five-phase flow is unchanged in structure; only path resolution and one scaffolding step change.

- **Path prefixing.** Define the active corpus root `C = corpora/<active-corpus>`. Every path the skill uses — `papers/`, `text/<slug>.md`, `notes/<slug>.md`, `_duplicates/`, `index.yaml`, `refs.yaml`, `INDEX.md`, `LANDSCAPE.md` — becomes `C/…`. Temp extraction to `/tmp` is unchanged.
- **First-sync scaffolding.** If the active corpus folder contains only `papers/` (no `index.yaml`), Phase 3 creates the skeleton (`text/`, `notes/`, `_duplicates/`, `index.yaml`, `refs.yaml`) as it ingests, and Phase 4 writes the first `INDEX.md`/`LANDSCAPE.md`. This is how a corpus created by bare `mkdir` becomes live.
- **New-PDF detection scope.** Phase 1's "new iff its sha256 is absent from `index.yaml`" reads only the active corpus's `index.yaml` and `papers/`.

## Hook changes — `select-corpus.sh`

The existing `detect-new-papers.sh` is repurposed and renamed. Its old job (grep unindexed PDFs against a root `index.yaml`) is removed entirely — that responsibility now lives only inside `/sync`, scoped to the active corpus.

New behavior: list `corpora/*` folder names, emit them with the selection instruction (or the empty-`corpora/` instruction). It reads no file contents. The hook registration in settings is updated to the new filename.

## `.gitignore` changes

Simplifies. Instead of ignoring root-level `papers/*`, `text/*`, … it ignores the whole corpus data tree and the marker:

```
corpora/*
!corpora/.gitkeep
.active-corpus
```

The machinery at the root stays tracked; `corpora/.gitkeep` keeps the empty container in the template so a fresh clone has somewhere to create the first corpus.

## Migration (one-time, local)

The current root corpus is all gitignored, so migration is a plain local move — no git history to rewrite:

```
mkdir -p corpora/floorplan-generation
mv papers text notes _duplicates index.yaml refs.yaml INDEX.md LANDSCAPE.md corpora/floorplan-generation/
```

Slugs are frozen and unaffected; internal relative references (`_duplicates/…` in `index.yaml`) still resolve because the whole tree moves together. The corpus folder name (`floorplan-generation`) is not frozen and may be renamed later. After migration, the root `papers/`, `text/`, etc. no longer exist; only `corpora/` and the machinery remain.

## Error handling and edge cases

- **Empty `corpora/`** → hook instructs the user to create a corpus; no selection is possible until one exists.
- **User names a non-existent corpus** → agent re-asks; it never creates a corpus from a mistyped name.
- **Stale `.active-corpus` from a prior session** → ignored at session start; every session re-asks and overwrites it on selection.
- **Context compaction mid-session** → active corpus recovered from `.active-corpus`; no re-ask.
- **Corpus folder with `papers/` but no `index.yaml`** → treated as new; scaffolded on first `/sync`.
- **Concurrent sessions in one checkout** → unsupported; single marker, last selection wins. Out of scope.
- **Nothing destructive.** Migration is a move of gitignored data; no machinery or held entry is deleted.

## Testing / acceptance

This workspace has no automated suite — verification is shell presence-checks plus one live acceptance run, exercised on a checkout containing two corpora:

1. **Pre-selection silence.** Start a session with two corpora present. Confirm the hook lists exactly the two folder names and that no corpus file (papers, index, cards) is read before the user answers.
2. **Selection + marker.** Name a corpus; confirm `.active-corpus` is written with that name and the agent reports the active corpus.
3. **Scoped grounding.** Ask a question; confirm the answer is grounded only in the active corpus and citations resolve under `corpora/<name>/text/`.
4. **Firewall.** Ask a cross-corpus question; confirm the agent refuses and offers to answer within the active corpus.
5. **Scoped sync.** Run `/sync`; confirm it reads and writes only under the active corpus and detects only that corpus's new PDFs.
6. **New corpus.** `mkdir corpora/<new>/papers`, add a PDF; confirm it appears in the next session's list, and that selecting it + `/sync` scaffolds the skeleton and ingests.
7. **Compaction recovery.** Force/observe a compaction mid-session; confirm the agent continues on the same corpus via `.active-corpus` without re-asking.
8. **Migration.** Move the existing corpus under `corpora/floorplan-generation/`; confirm slugs are unchanged and questions are still answered correctly.

## Explicitly cut (YAGNI)

- Cross-corpus queries and comparisons.
- Mid-session corpus switching (a `/switch` command).
- Concurrent sessions on different corpora in one checkout.
- Per-corpus machinery versions (all corpora share the root machinery).
- A `/new-corpus` helper command — bare `mkdir` + first-sync scaffolding is the creation path.
- Proactive new-PDF detection on selection — detection stays inside `/sync`.
