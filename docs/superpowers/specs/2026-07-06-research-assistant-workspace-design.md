# Research Assistant Workspace — Design

**Date:** 2026-07-06
**Status:** Awaiting user approval

## What this is

A personal research assistant for the early/exploratory stage of a research project, running entirely inside Claude Code. The user drops paper PDFs into a folder; the assistant (1) organizes them — dedupe, one-time renaming, human-readable overview — and (2) answers questions grounded strictly in those papers, with verifiable citations, starting broad (corpus-level story) and drilling down into fewer papers as questions get more specific.

**Scale target:** 10–100 papers. Explicitly out of scope: RAG/embeddings/vector DBs, any app or database. The deliverable is a *workspace* — folder conventions, a `CLAUDE.md` with behavioral rules, a SessionStart hook, and skills — not a program.

## Folder layout

```
claude-research-agent/
├── CLAUDE.md              # grounding + workflow rules (the "brain stem")
├── index.yaml             # machine source of truth: one entry per paper
├── INDEX.md               # human overview sheet — GENERATED from index.yaml, never hand-edited
├── LANDSCAPE.md           # the story: narrative + Mermaid relation graph — GENERATED
├── papers/                # the PDFs, renamed once at ingestion: YYYY-firstauthor-short-title.pdf
├── text/                  # extracted text cache: <slug>.md per paper (pdftotext output)
├── notes/                 # one card per paper: <slug>.md
├── _duplicates/           # dedupe losers moved here — nothing is ever deleted
├── .claude/
│   ├── settings.json      # SessionStart hook registration
│   ├── hooks/detect-new-papers.sh
│   └── skills/            # /sync skill (ingestion + regeneration)
└── docs/superpowers/specs/  # this document
```

## Identity and naming

- **Slug** = `YYYY-firstauthor-short-title` (kebab-case). Assigned once at first ingestion, **frozen forever**. The slug is simultaneously: filename stem, citation key, text-cache name, card name, and graph node id.
- **Paper identity for dedupe:** DOI or arXiv ID when available; fallback fuzzy match on title + authors. Preprint vs camera-ready = same paper (keep published/latest). Duplicates are moved to `_duplicates/` with the verdict recorded in `index.yaml` — never deleted.

## index.yaml — machine source of truth

One entry per paper:

```yaml
- slug: 2023-smith-contrastive-distillation
  title: "..."
  authors: [Smith, J., ...]
  year: 2023
  venue: "..."            # verified via Crossref/arXiv when online; else best-effort from PDF
  ids: {doi: "...", arxiv: "..."}
  original_filename: "2301.04567v2.pdf"
  file_hash: sha256:...
  summary: "One line."     # enables index-only answers to 'which papers…' questions
  tags: [contrastive-learning, distillation, imagenet]
  status: ok               # ok | needs-ocr | metadata-unverified
  relations:
    - {to: 2021-doe-simclr-v3, type: builds-on, why: "extends its objective, §3.1"}
      # types: builds-on | same-method-family | same-dataset | competes-with | surveys
```

Every relation edge carries a one-line justification — the graph stays groundable like everything else.

## Generated human artifacts

- **INDEX.md** — readable table (slug, title, year, venue, tags, one-liner, status). Regenerated from `index.yaml` on every sync.
- **LANDSCAPE.md** — the corpus *story*: thematic clusters, what each cluster tries to solve, how clusters connect, open tensions — plus a Mermaid graph of the typed relations (nodes = slugs, edges labeled by type). Regenerated on sync. Mermaid-first; an interactive HTML artifact is a possible v2, not built now.

## Per-paper card — notes/<slug>.md

Structured summary written at ingestion: problem, method, datasets/benchmarks, key results **with page-anchored direct quotes**, limitations, and its relations to other corpus papers. Cards are the *routing* layer for Q&A — never the final grounding for a specific claim (see Q&A rules).

## Ingestion workflow (per new paper)

Triggered via `/sync` or when the session-start detection reports new files. Steps:

1. **Extract** text with `pdftotext` → `text/<slug>.md` (extract once, cache forever).
2. **OCR check:** if text yield is low (chars/page below threshold), mark `status: needs-ocr`, keep the paper listed, and disclose the gap whenever the paper would be relevant to a question. No auto-OCR in v1 (tracked as a possible future feature).
3. **Metadata:** extract candidates from the PDF, verify via Crossref/arXiv title search when online; else mark `metadata-unverified`.
4. **Dedupe** per identity rules; losers → `_duplicates/`.
5. **Rename** the PDF to its slug — as part of a **dry-run plan the user approves** (rename table + dupe verdicts shown first, then executed). This is the only time the file is ever renamed.
6. **Card** written to `notes/<slug>.md`.
7. **Index** entry added (tags, one-liner, relations with justifications).
8. **Regenerate** `INDEX.md` and `LANDSCAPE.md`.

Sync is **incremental**, keyed on file hash: only new/changed files are processed; orphans (index entries whose PDF vanished) are reported, not auto-removed.

## Session-start detection

A SessionStart hook runs a fast script: hash the PDFs in `papers/`, diff against `index.yaml`, and inject a context note ("N new PDFs detected: …"). The hook only **detects**. The agent then **asks the user** before running ingestion ("3 new papers found — ingest them?"), and executes on confirmation. Ingestion is never buried inside the hook.

## Q&A: tiered routing (Option A)

Cheapest tier first; each tier either answers or routes deeper. This also produces the desired conversational shape: broad story first, then deeper into fewer papers.

- **Tier 0 — LANDSCAPE.md:** corpus-level questions ("what do my papers cover, how do they relate?").
- **Tier 1 — index.yaml (tags + one-liners):** "which papers use X" survey questions.
- **Tier 2 — cards:** orientation on the shortlisted papers.
- **Tier 3 — grep over `text/`:** finds anything the cards missed; catches questions outside what was noted.
- **Tier 4 — full-text read** of the 2–4 matching papers' extracted text before answering anything specific.
- **Escalation — subagent fan-out** across the corpus for genuinely whole-corpus deep questions (e.g., "compare evaluation protocols across all papers").

**The load-bearing rule (in CLAUDE.md): cards and index may *route*; only full text may *ground*.** No substantive claim is answered from a card alone; quantitative claims are re-verified against `text/<slug>.md`.

## Grounding & citation rules (CLAUDE.md)

- Every claim cites `[slug]`, with section/page when possible: `[2023-smith-contrastive-distillation, §5.2]`.
- Load-bearing claims include the direct quote, so any citation is verifiable in seconds by grepping the text cache.
- Knowledge from outside the corpus must be explicitly labeled as such; "this is not covered in your papers" is a required answer when true.
- Papers with `needs-ocr` or `metadata-unverified` status are disclosed when relevant.

## Error handling

- Extraction failure / garbage output → `needs-ocr` or `status` flag; never silently dropped.
- Offline during ingestion → `metadata-unverified`; re-verification attempted on later syncs.
- Dedupe uncertainty (fuzzy match below confidence) → ask the user in the dry-run plan rather than deciding.
- Nothing destructive ever happens without the dry-run approval; nothing is ever deleted.

## Testing / acceptance

Verified by exercising the real flows with a handful of real PDFs (including one scanned PDF and one duplicate pair):

1. Drop 5 PDFs → start session → hook reports 5 new → user confirms → ingestion produces correct renames (after approval), cards, index entries, INDEX.md, LANDSCAPE.md with Mermaid graph.
2. Duplicate pair → one lands in `_duplicates/` with recorded verdict.
3. Scanned PDF → flagged `needs-ocr`, disclosed when queried.
4. "Which papers use X?" answered from index/tags with correct slugs; a deep quantitative question shows full-text-grounded quotes with page anchors.
5. Add 2 more PDFs → sync processes only those 2; landscape updates.

## Repo as a replicable template

The workspace lives in a GitHub repo, but only the *machinery* is versioned — anyone can clone it, drop their own PDFs into `papers/`, and generate their own index/cards/landscape. `.gitignore` excludes everything corpus-derived:

```gitignore
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

Committed: `CLAUDE.md`, `.claude/` (hook script, settings, skills), `docs/`, `README.md` (what this is + how to use it with your own papers), `.gitignore`, and `.gitkeep` files so the empty `papers/` directory structure survives cloning.

## Explicitly cut from v1 (tracked for later)

Auto-OCR, BibTeX export, Zotero sync, auto-downloading missing papers, PDF annotation, interactive HTML graph, embeddings/search index (revisit only past ~300 papers).
