# Research Assistant Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a replicable Claude Code workspace that organizes paper PDFs (dedupe, one-time rename, index, cards, landscape) and answers questions grounded strictly in those papers with verifiable citations.

**Architecture:** No app, no database, no embeddings. The deliverable is a workspace: folder conventions + `CLAUDE.md` behavioral rules + a SessionStart detection hook + a `/sync` ingestion skill. All state lives in plain files (`index.yaml` is machine truth; `INDEX.md`/`LANDSCAPE.md` are generated). Q&A uses tiered routing: landscape → index → cards → grep → full text, with the rule "cards route, only full text grounds."

**Tech Stack:** Bash (hook script), Markdown/YAML (all artifacts), `pdftotext` from poppler (extraction), `gh` CLI (repo creation). macOS host (`shasum -a 256`).

**Spec:** `docs/superpowers/specs/2026-07-06-research-assistant-workspace-design.md`

## Global Constraints

- No RAG/embeddings/vector DB; no app or database. Plain files only.
- Slug format `YYYY-firstauthor-short-title` (kebab-case), assigned once at ingestion, **frozen forever**.
- Nothing is ever deleted; dedupe losers move to `_duplicates/`.
- Renames and dupe moves only happen after a user-approved dry-run plan.
- `INDEX.md` and `LANDSCAPE.md` are generated from `index.yaml`, never hand-edited.
- Corpus-derived files are gitignored (`papers/*`, `text/*`, `notes/*`, `_duplicates/*`, `index.yaml`, `INDEX.md`, `LANDSCAPE.md`); machinery is committed.
- Citations: `[slug]` or `[slug, §X / p.N]`; load-bearing claims carry direct quotes.
- Session-start behavior: hook **detects only**; agent asks the user, then ingests.

---

### Task 1: Folder scaffold + .gitignore template behavior

**Files:**
- Create: `.gitignore`
- Create: `papers/.gitkeep`, `text/.gitkeep`, `notes/.gitkeep`, `_duplicates/.gitkeep`

**Interfaces:**
- Produces: the directory layout every later task references; git-ignore behavior that keeps corpus files out of the repo while `.gitkeep` files preserve empty dirs.

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Corpus-derived content stays local — this repo is a replicable template.
papers/*
text/*
notes/*
_duplicates/*
!papers/.gitkeep
!text/.gitkeep
!notes/.gitkeep
!_duplicates/.gitkeep
index.yaml
INDEX.md
LANDSCAPE.md
```

- [ ] **Step 2: Create directories with .gitkeep files**

```bash
mkdir -p papers text notes _duplicates
touch papers/.gitkeep text/.gitkeep notes/.gitkeep _duplicates/.gitkeep
```

- [ ] **Step 3: Verify ignore behavior with fixtures**

```bash
touch papers/fixture.pdf text/fixture.md notes/fixture.md _duplicates/fixture.pdf index.yaml INDEX.md LANDSCAPE.md
git check-ignore papers/fixture.pdf text/fixture.md notes/fixture.md _duplicates/fixture.pdf index.yaml INDEX.md LANDSCAPE.md
```

Expected: all seven paths printed (all ignored), exit code 0.

```bash
git status --porcelain
```

Expected output contains exactly the machinery: `.gitignore` and the four `.gitkeep` files as untracked/added — **no** fixture files, no `index.yaml`/`INDEX.md`/`LANDSCAPE.md`.

- [ ] **Step 4: Remove fixtures**

```bash
rm papers/fixture.pdf text/fixture.md notes/fixture.md _duplicates/fixture.pdf index.yaml INDEX.md LANDSCAPE.md
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore papers/.gitkeep text/.gitkeep notes/.gitkeep _duplicates/.gitkeep
git commit -m "feat: workspace scaffold — template gitignore keeps corpus local"
```

---

### Task 2: CLAUDE.md — grounding rules and tiered routing

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: folder layout from Task 1.
- Produces: the behavioral contract every session loads. References `/sync` (defined in Task 4) and the detection hook (Task 3) — those names must match exactly: skill `sync`, hook script `.claude/hooks/detect-new-papers.sh`.

- [ ] **Step 1: Write `CLAUDE.md` with this exact content**

````markdown
# Research Assistant Workspace

You are a research assistant grounded in the papers in this workspace. The corpus is the PDFs in `papers/`, with extracted text cached in `text/<slug>.md`, per-paper cards in `notes/<slug>.md`, machine metadata in `index.yaml`, and generated human views `INDEX.md` (overview table) and `LANDSCAPE.md` (corpus story + relation graph).

## Answering questions: tiered routing

Route every question through the cheapest sufficient tier; escalate until the answer is grounded. This also shapes conversation: broad story first, then deeper into fewer papers.

- **Tier 0 — `LANDSCAPE.md`:** corpus-level questions (what the papers cover, how they relate, the big picture).
- **Tier 1 — `index.yaml` (tags + one-line summaries):** "which papers use/do X" survey questions.
- **Tier 2 — `notes/<slug>.md` cards:** orientation on the shortlisted papers.
- **Tier 3 — grep over `text/`:** locate content the cards missed; catches questions outside what was noted.
- **Tier 4 — read the full `text/<slug>.md`** of the 2–4 relevant papers before answering anything specific.
- **Escalation:** for genuinely whole-corpus deep questions (e.g., "compare evaluation protocols across all papers"), fan out subagents, each reading a share of `text/`, then merge.

**Load-bearing rule: cards and index may ROUTE; only full text may GROUND.** Never answer a substantive question from a card or the index alone. Re-verify every quantitative claim against `text/<slug>.md` before stating it.

## Grounding and citations

- Every corpus claim cites `[slug]`, with section/page when possible: `[2023-smith-contrastive-distillation, §5.2]`.
- Load-bearing claims include a direct quote, so any citation can be verified in seconds by grepping `text/`.
- Knowledge from outside the corpus must be explicitly labeled "(outside your corpus)".
- If the papers don't cover something, say "this is not covered in your papers." That is a required answer, not a failure.
- When a paper with `status: needs-ocr` or `metadata-unverified` is relevant to a question, disclose that limitation.

## Ingestion and file discipline

- A SessionStart hook (`.claude/hooks/detect-new-papers.sh`) reports PDFs not yet in `index.yaml`. When it reports new papers, **ask the user** whether to ingest, then run the `sync` skill on confirmation. The hook never ingests.
- Slugs (`YYYY-firstauthor-short-title`) are assigned once at first ingestion and **frozen forever** — never rename a paper afterward.
- Never delete files. Duplicates are moved to `_duplicates/` with the verdict recorded in `index.yaml`.
- Renames and duplicate moves always go through a dry-run plan the user approves first.
- `INDEX.md` and `LANDSCAPE.md` are generated from `index.yaml` — never hand-edit them; regenerate via the `sync` skill.
````

- [ ] **Step 2: Verify internal references**

```bash
grep -c "sync" CLAUDE.md && grep -c "detect-new-papers.sh" CLAUDE.md
```

Expected: both counts ≥ 1.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: CLAUDE.md — tiered routing, grounding rules, ingestion discipline"
```

---

### Task 3: SessionStart detection hook

**Files:**
- Create: `.claude/hooks/detect-new-papers.sh`
- Create: `.claude/settings.json`

**Interfaces:**
- Consumes: `papers/` layout (Task 1); `index.yaml` schema field `file_hash: sha256:<hex>` (defined in Task 4 — the hook only greps for the hex digest substring, so plain-text presence of the digest anywhere in `index.yaml` is the contract).
- Produces: stdout lines injected as session context when new PDFs exist; silent (no output, exit 0) otherwise.

- [ ] **Step 1: Write the failing test (fixture run before the script exists)**

```bash
bash .claude/hooks/detect-new-papers.sh
```

Expected: FAIL — `no such file or directory`.

- [ ] **Step 2: Write `.claude/hooks/detect-new-papers.sh`**

```bash
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
```

```bash
chmod +x .claude/hooks/detect-new-papers.sh
```

- [ ] **Step 3: Test — new PDF is detected**

```bash
printf 'dummy pdf bytes' > papers/hooktest.pdf
bash .claude/hooks/detect-new-papers.sh
```

Expected output:

```
NEW PAPERS DETECTED: 1 PDF(s) in papers/ are not in index.yaml:
 - papers/hooktest.pdf
Ask the user whether to ingest them now with the sync skill. Do not ingest without asking.
```

- [ ] **Step 4: Test — indexed PDF is silent**

```bash
h=$(shasum -a 256 papers/hooktest.pdf | awk '{print $1}')
printf -- "- slug: hooktest\n  file_hash: sha256:%s\n" "$h" > index.yaml
bash .claude/hooks/detect-new-papers.sh; echo "exit=$?"
```

Expected: no detection output, then `exit=0`.

- [ ] **Step 5: Test — empty papers dir and missing index.yaml are silent**

```bash
rm papers/hooktest.pdf index.yaml
bash .claude/hooks/detect-new-papers.sh; echo "exit=$?"
```

Expected: no output except `exit=0`.

- [ ] **Step 6: Write `.claude/settings.json`**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/detect-new-papers.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 7: Validate settings JSON**

```bash
python3 -m json.tool .claude/settings.json
```

Expected: pretty-printed JSON, exit 0.

- [ ] **Step 8: Commit**

```bash
git add .claude/hooks/detect-new-papers.sh .claude/settings.json
git commit -m "feat: SessionStart hook detects unindexed PDFs (detect-only)"
```

---

### Task 4: /sync ingestion skill

**Files:**
- Create: `.claude/skills/sync/SKILL.md`

**Interfaces:**
- Consumes: folder layout (Task 1), hook contract (Task 3: `file_hash: sha256:<hex>` must appear verbatim in each index entry so the hook's grep works).
- Produces: the full ingestion procedure, the `index.yaml` entry schema, the card template, and INDEX.md/LANDSCAPE.md generation rules. CLAUDE.md (Task 2) refers to this skill by the name `sync`.

- [ ] **Step 1: Write `.claude/skills/sync/SKILL.md` with this exact content**

````markdown
---
name: sync
description: Ingest new or changed PDFs in papers/ — extract text, verify metadata, dedupe, rename once (after dry-run approval), write per-paper cards, update index.yaml, and regenerate INDEX.md and LANDSCAPE.md. Use when the session-start hook reports new papers or the user asks to sync/organize the corpus.
---

# /sync — corpus ingestion and regeneration

Incremental by design: a PDF is "new" iff its sha256 does not appear in `index.yaml`. Also report **orphans** (index entries whose PDF no longer exists in `papers/` or `_duplicates/`) — report only, never auto-remove.

Prerequisite: `pdftotext` (poppler). If missing, stop and tell the user to run `brew install poppler`.

## Phase 1 — Analyze (no file changes yet)

For each new PDF:

1. **Extract** text: `pdftotext -layout papers/<file>.pdf /tmp/<file>.txt`.
2. **OCR check:** compute characters per page (total chars ÷ page count from `pdfinfo` or extraction output). If < 200 chars/page, the paper gets `status: needs-ocr`; it is still indexed and carded from whatever text exists, with the limitation noted in the card.
3. **Metadata:** read the first 2 pages of extracted text; identify title, authors, year, venue, DOI, arXiv ID candidates. Verify online when possible:
   - Crossref: `https://api.crossref.org/works?query.title=<title>&rows=3` — match by title similarity + first author.
   - arXiv: `http://export.arxiv.org/api/query?search_query=ti:"<title>"&max_results=3`.
   - If offline or no confident match: `status: metadata-unverified`, best-effort fields from the PDF.
4. **Slug:** `YYYY-firstauthor-short-title` — year, first author's family name (lowercase), 3–6 word kebab-case title fragment. On collision, extend the title fragment.
5. **Dedupe verdict:** the paper is a duplicate of an index entry if they share a DOI or arXiv ID, or if title + author list match fuzzily (near-identical title, same first author). Preprint vs camera-ready = same paper: **keep the published/latest version**, move the other to `_duplicates/`. If the fuzzy match is not confident, mark the verdict "uncertain — user decides" for Phase 2.

## Phase 2 — Dry-run approval (REQUIRED before any file changes)

Present one plan table to the user:

| current file | action | slug / destination | dedupe verdict |
|---|---|---|---|
| `2301.04567v2.pdf` | rename | `papers/2023-smith-contrastive-distillation.pdf` | new paper |
| `smith_preprint.pdf` | move | `_duplicates/smith_preprint.pdf` | duplicate of 2023-smith-… (arXiv id match) |

Include uncertain dedupe cases as explicit questions. **Wait for approval. Do not touch files before it.**

## Phase 3 — Execute

Per approved row:

1. Rename PDF to `papers/<slug>.pdf` (this is the ONLY time this file is ever renamed) or move duplicate to `_duplicates/` (keep its original name there).
2. Save extracted text to `text/<slug>.md`.
3. Write the card to `notes/<slug>.md` (template below).
4. Append the entry to `index.yaml` (schema below).

## Phase 4 — Regenerate

1. **`INDEX.md`** — generated table over all `index.yaml` entries, sorted by year desc: `| slug | title | year | venue | tags | one-line summary | status |`. Header note: "Generated from index.yaml — do not edit by hand."
2. **`LANDSCAPE.md`** — the corpus story, regenerated from `index.yaml` + cards:
   - Thematic clusters (from tags/relations): what each cluster is trying to solve, which papers belong, how clusters connect, and where the open tensions/gaps are. Narrative prose, not bullets-only.
   - A Mermaid `graph TD` of relations: nodes are slugs, edges labeled with the relation type. Same generated-file header note.
3. Report orphans and any `needs-ocr` / `metadata-unverified` statuses in the final summary to the user.

## index.yaml entry schema

```yaml
- slug: 2023-smith-contrastive-distillation
  title: "Contrastive Distillation for ..."
  authors: ["Smith, J.", "Doe, A."]
  year: 2023
  venue: "NeurIPS 2023"
  ids: {doi: "10.5555/...", arxiv: "2301.04567"}
  original_filename: "2301.04567v2.pdf"
  file_hash: sha256:<full hex digest>   # verbatim digest — the session hook greps for it
  summary: "One sentence: what it does and why it matters."
  tags: [contrastive-learning, distillation, imagenet]
  status: ok        # ok | needs-ocr | metadata-unverified
  relations:
    - {to: 2021-doe-simclr-v3, type: builds-on, why: "extends its objective, §3.1"}
      # types: builds-on | same-method-family | same-dataset | competes-with | surveys
```

Every relation edge carries a one-line `why` justification grounded in the paper.

## Card template — notes/<slug>.md

```markdown
# <Title> [<slug>]

**Problem:** what gap or question the paper addresses.
**Method:** the approach, in enough detail to route method questions here.
**Datasets/benchmarks:** what it evaluates on.
**Key results:** the headline numbers/claims — each with a page-anchored direct quote:
> "…exact quote…" (p. 7)
**Limitations:** stated or evident weaknesses.
**Relations:** how it connects to other corpus papers (mirror of index relations).
```

Cards are the ROUTING layer. They must never be the final grounding for a specific claim — full text in `text/<slug>.md` is.
````

- [ ] **Step 2: Verify skill frontmatter and hook contract consistency**

```bash
head -4 .claude/skills/sync/SKILL.md | grep "name: sync"
grep -c "file_hash: sha256:" .claude/skills/sync/SKILL.md
```

Expected: `name: sync` printed; count ≥ 1.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/sync/SKILL.md
git commit -m "feat: /sync skill — analyze, dry-run approval, execute, regenerate"
```

---

### Task 5: README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: everything above; documents the clone-and-use flow for a fresh user.

- [ ] **Step 1: Write `README.md` with this exact content**

````markdown
# Claude Research Agent

A replicable [Claude Code](https://claude.com/claude-code) workspace that turns a folder of paper PDFs into an organized, queryable research corpus. No app, no database, no embeddings — plain files plus agent conventions.

**What it does**

1. **Organizes:** dedupes, renames each paper once to a stable `YYYY-firstauthor-short-title` slug, extracts a text cache, writes a structured card per paper, and maintains `index.yaml` (machine truth) → generated `INDEX.md` (overview table) and `LANDSCAPE.md` (the story of your corpus + a Mermaid relation graph).
2. **Answers questions grounded in YOUR papers,** with checkable citations (`[slug, §5.2]` + direct quotes), starting broad and drilling into fewer papers as you go deeper. If your papers don't cover it, it says so.

**Requirements**

- Claude Code
- `pdftotext` from poppler: `brew install poppler`

**Use with your own papers**

```bash
git clone <this-repo> my-research && cd my-research
cp ~/Downloads/*.pdf papers/
claude
```

On session start, a hook detects the new PDFs and Claude asks to ingest them. Ingestion shows you a dry-run plan (renames + duplicate verdicts) before touching any file. Then just ask questions.

**What stays local**

Your PDFs and everything derived from them (`papers/`, `text/`, `notes/`, `_duplicates/`, `index.yaml`, `INDEX.md`, `LANDSCAPE.md`) are gitignored. The repo carries only the machinery, so it can be reused on any set of papers.

**Guarantees**

- Nothing is ever deleted; duplicates move to `_duplicates/`.
- Files are renamed exactly once, at ingestion, after your approval.
- Answers cite papers verifiably or explicitly say the corpus doesn't cover the question.

**Not in v1 (tracked):** OCR for scanned PDFs (they're flagged `needs-ocr`), BibTeX export, Zotero sync, interactive graph. Design docs live in `docs/superpowers/specs/`.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README — template usage, guarantees, requirements"
```

---

### Task 6: GitHub repo + end-to-end smoke test

**Files:**
- No new files (repo push + live verification).

**Interfaces:**
- Consumes: all previous tasks.

- [ ] **Step 1: Verify gh auth**

```bash
gh auth status
```

Expected: logged-in account shown. If not, stop and ask the user to run `! gh auth login`.

- [ ] **Step 2: Create private repo and push**

```bash
gh repo create claude-research-agent --private --source=. --push
```

Expected: repo URL printed; `git push` succeeds. (Private by default; flip later with `gh repo edit --visibility public` if desired.)

- [ ] **Step 3: Confirm no corpus files are tracked**

```bash
git ls-files | grep -E '^(papers|text|notes|_duplicates)/' | grep -v '.gitkeep'; echo "exit=$?"
```

Expected: no output, then `exit=1` (grep found nothing).

- [ ] **Step 4: Smoke-test detection with a real PDF**

```bash
curl -sL -o papers/attention.pdf https://arxiv.org/pdf/1706.03762
bash .claude/hooks/detect-new-papers.sh
```

Expected: `NEW PAPERS DETECTED: 1 PDF(s)…  - papers/attention.pdf`.

- [ ] **Step 5: Live acceptance (agent work, not shell)**

With `papers/attention.pdf` present, run the `sync` skill end-to-end in-session: expect extraction to `text/`, metadata verified via arXiv, a dry-run rename plan (approve it), a card in `notes/`, an `index.yaml` entry whose `file_hash` silences the hook on re-run, and generated `INDEX.md` + `LANDSCAPE.md` (single-node Mermaid graph). Then ask one grounded question ("what attention mechanism does my corpus use?") and verify the answer cites `[2017-vaswani-attention-is-all-you-need]` with a quote. To exercise dedupe, download an older version of the same paper (`curl -sL -o papers/attention-v1.pdf https://arxiv.org/pdf/1706.03762v1`) and re-run `sync`: the dry-run must flag it as a duplicate (same arXiv ID), and on approval it moves to `_duplicates/` with the verdict recorded in `index.yaml`. Finally remove the test artifacts (`papers/*.pdf` except `.gitkeep`, `text/*`, `notes/*`, `index.yaml`, `INDEX.md`, `LANDSCAPE.md`) or keep them if the user wants — they're gitignored either way.

- [ ] **Step 6: Final push**

```bash
git push
```

Expected: up to date (all commits already pushed) or pushes any stragglers.
