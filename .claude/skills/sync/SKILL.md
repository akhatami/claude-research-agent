---
name: sync
description: Ingest new or changed PDFs in papers/ — extract text, verify metadata, dedupe, rename once (after dry-run approval), write per-paper cards, update index.yaml, harvest referenced-but-not-held ghost papers into refs.yaml, and regenerate INDEX.md and LANDSCAPE.md. Use when the session-start hook reports new papers or the user asks to sync/organize the corpus.
---

# /sync — corpus ingestion and regeneration

**Active corpus.** `/sync` operates on exactly one corpus: the folder named in `.active-corpus`. Throughout this skill, `C` denotes `corpora/<active-corpus>/`. Every corpus path below — `papers/`, `text/`, `notes/`, `_duplicates/`, `index.yaml`, `refs.yaml`, `INDEX.md`, `LANDSCAPE.md` — lives under `C/`. If no corpus is selected yet, stop and ask the user to open one; never sync across corpora. (Temporary extraction to `/tmp` is not corpus-scoped.)

Incremental by design: a PDF is "new" iff its sha256 does not appear in `C/index.yaml`. On each sync, also re-attempt metadata verification for entries with `status: metadata-unverified`, updating them to `ok` on success. Also report **orphans** (index entries whose PDF no longer exists in `C/papers/` or `C/_duplicates/`) — report only, never auto-remove.

Prerequisite: `pdftotext` (poppler). If missing, stop and tell the user to run `brew install poppler`.

## Phase 1 — Analyze (no file changes yet)

For each new PDF:

1. **Extract** text: `pdftotext -layout C/papers/<file>.pdf /tmp/<file>.txt`.
2. **OCR check:** compute characters per page (total chars ÷ page count from `pdfinfo` or extraction output). If < 200 chars/page, the paper gets `status: needs-ocr`; it is still indexed and carded from whatever text exists, with the limitation noted in the card.
3. **Metadata:** read the first 2 pages of extracted text; identify title, authors, year, venue, DOI, arXiv ID candidates. Verify online when possible:
   - Crossref: `https://api.crossref.org/works?query.title=<title>&rows=3` — match by title similarity + first author.
   - arXiv: `http://export.arxiv.org/api/query?search_query=ti:"<title>"&max_results=3`.
   - If offline or no confident match: `status: metadata-unverified`, best-effort fields from the PDF.
4. **Slug:** `YYYY-firstauthor-short-title` — year, first author's family name (lowercase), 3–6 word kebab-case title fragment. On collision, extend the title fragment.
5. **Dedupe verdict:** the paper is a duplicate of an index entry if they share a DOI or arXiv ID, or if title + author list match fuzzily (near-identical title, same first author). Preprint vs camera-ready = same paper: **keep the published/latest version**, move the other to `C/_duplicates/`. If the fuzzy match is not confident, mark the verdict "uncertain — user decides" for Phase 2.

## Phase 2 — Dry-run approval (REQUIRED before any file changes)

Present one plan table to the user:

| current file | action | slug / destination | dedupe verdict |
|---|---|---|---|
| `2301.04567v2.pdf` | rename | `C/papers/2023-smith-contrastive-distillation.pdf` | new paper |
| `smith_preprint.pdf` | move | `C/_duplicates/smith_preprint.pdf` | duplicate of 2023-smith-… (arXiv id match) |
| `Lee_Benchmark_2019.pdf` | rename + promote | `C/papers/2019-lee-foundational-benchmark.pdf` | promotes ⟨ghost:2019-lee-foundational-benchmark⟩ → held paper |

Include uncertain dedupe cases as explicit questions. If a new PDF matches an existing ghost in `C/refs.yaml` (shared DOI/arXiv, or fuzzy title + first-author), present it as a **promotion**: on approval it is ingested as a normal held paper, and Phase 5 then removes its former ghost entry from `C/refs.yaml`. **Wait for approval. Do not touch files before it.**

## Phase 3 — Execute

**First sync of a new corpus:** if `C/` contains only `papers/` (no `C/index.yaml`), create the skeleton before ingesting — `C/text/`, `C/notes/`, `C/_duplicates/`, an empty `C/index.yaml`, and an empty `C/refs.yaml`. This is how a corpus created by a bare `mkdir corpora/<name>/papers` becomes live.

Per approved row:

1. Rename PDF to `C/papers/<slug>.pdf` (this is the ONLY time this file is ever renamed) or move duplicate to `C/_duplicates/` (keep its original name there). When moving a duplicate, record the verdict in the KEEPER's `C/index.yaml` entry under its `duplicates:` list (schema below) — recording the hash preserves provenance and suppresses re-detection if the same file is dropped into `C/papers/` again.
2. Save extracted text to `C/text/<slug>.md`.
3. Write the card to `C/notes/<slug>.md` (template below).
4. Append the entry to `C/index.yaml` (schema below).

## Phase 4 — Regenerate

1. **`C/INDEX.md`** — generated table over all `C/index.yaml` entries (held papers only — ghosts never appear here), sorted by year desc: `| slug | title | year | venue | tags | one-line summary | status |`. Header note: "Generated from index.yaml — do not edit by hand."
2. **`C/LANDSCAPE.md`** (held content) — the corpus story, regenerated from `C/index.yaml` + cards. Held papers only here; the ghost surfaces are added afterward by Phase 5 (which owns `C/refs.yaml`):
   - Thematic clusters (from tags/relations): what each cluster is trying to solve, which papers belong, how clusters connect, and where the open tensions/gaps are. Narrative prose, not bullets-only.
   - A Mermaid `graph TD` of relations over HELD papers only: nodes use short hyphen-free aliases (the slug or title in the node label), edges labeled with the relation type. Keep node ids hyphen-free for Mermaid compatibility. Ghost nodes are added by Phase 5 — do not draw them here. Same generated-file header note.
3. Report orphans and any `needs-ocr` / `metadata-unverified` statuses in the final summary to the user.

## Phase 5 — Harvest ghosts (referenced-but-not-held papers)

Runs after Phase 4 on every sync. Produces/updates `C/refs.yaml` and the ghost surfaces in `C/LANDSCAPE.md`. Ghosts are sourced ONLY from held papers' own bibliographies — no external lookup for discovery.

1. **Extract bibliographies:** for each held paper, take the References/Bibliography section from `C/text/<slug>.md` (the tail after the last "References"/"Bibliography" heading).
2. **Parse & normalize** each reference entry → first-author surname, year, title fragment, DOI/arXiv id if present. Bibliographies from `status: needs-ocr` papers may be garbled — best-effort only.
3. **Resolve against held papers first:** if a reference matches an existing `C/index.yaml` slug (shared DOI/arXiv, or fuzzy title + first-author), it is a held→held citation, NOT a ghost — exclude it from the ghost pass. (Writing that citation as a real `relations:` edge is the deferred relations-backfill; for now it is only excluded from ghosting.)
4. **Match/merge across papers:** group references that are the same work — exact by shared DOI/arXiv, else fuzzy on first-author + year + title. When a match is ambiguous, DO NOT merge (two near-duplicate ghosts is a smaller harm than a wrong merge). Each surviving group gets a `cited_by` list of the held slugs that reference it.
5. **Select (hybrid):** keep a group as a ghost iff `len(cited_by) ≥ 2`, OR it is carried forward as `status: pinned`. Exclude any group whose key is `status: rejected`. Non-pinned singletons are excluded.
6. **Assign keys & reconcile with existing `C/refs.yaml`:**
   - New ghost → `key` = `YYYY-firstauthor-short-title` (same shape as a slug), frozen once assigned.
   - Existing ghost → preserve its `key`, `status`, and `note`; refresh `cited_by` and enriched fields.
   - **Promotion:** if a ghost now matches a paper newly held after this sync's Phase 3, remove it from `C/refs.yaml` (it has graduated). Its former `cited_by` are the held papers that cite it; converting those into real held→held `relations:` edges is **deferred** (the relations-backfill follow-up), because each such edge is outbound `{to: <promoted-slug>}` on the *citer's* own entry — not on the promoted paper's — and the relation `type` enum has no bare-citation type. Until backfill ships, promotion graduates the paper and drops the ghost only.
7. **Enrich (best-effort, above-threshold ghosts only):** verify metadata via Crossref/arXiv exactly as Phase 1 does, filling `venue`/`ids`. Offline or no confident match → leave best-effort `title`/`year` with `ids: null`; retried on later syncs.
8. **Write `C/refs.yaml`** (schema below), then render the ghost surfaces into `C/LANDSCAPE.md` (Phase 5 owns these; Phase 4 has already written the held content):
   - **Promotion-candidate table** — a section **Ghost papers — referenced but not held (promotion candidates)**: a table sorted by pull (`count = len(cited_by)`) descending — `| ghost | year | pull | status | cited by | why |`. The `status` column shows `candidate` or `pinned` (pinned singletons are intentional, so they read correctly at `pull 1`). This is the promotion shortlist; the ghosts whose absence most weakens the corpus sit at the top.
   - **Ghost nodes in the Mermaid graph** — draw only the top ~8 ghosts by pull to keep the graph readable (the table lists ALL ghosts). Each drawn ghost gets a hyphen-free node id `ghost_<key>` (hyphens in `<key>` → underscores), styled distinctly (dashed border, dimmed) via a `classDef ghost`, with edges labeled `references` from up to 3 of its citing held papers.

Curation verdicts persist across syncs: a ghost the user dismisses is recorded `status: rejected` with a `note` and never re-surfaces; a foundational singleton the agent keeps is `status: pinned` with a `note` reason.

## index.yaml entry schema

Entries live in `C/index.yaml`.

```yaml
- slug: 2023-smith-contrastive-distillation
  title: "Contrastive Distillation for ..."
  authors: ["Smith, J.", "Doe, A."]
  year: 2023
  venue: "NeurIPS 2023"
  ids: {doi: "10.5555/...", arxiv: "2301.04567"}
  original_filename: "2301.04567v2.pdf"
  file_hash: sha256:<full hex digest>   # verbatim digest — /sync Phase 1 greps for it
  summary: "One sentence: what it does and why it matters."
  tags: [contrastive-learning, distillation, imagenet]
  status: ok        # ok | needs-ocr | metadata-unverified
  relations:
    - {to: 2021-doe-simclr-v3, type: builds-on, why: "extends its objective, §3.1"}
      # types: builds-on | same-method-family | same-dataset | competes-with | surveys
  duplicates:
    - {file: "_duplicates/attention-v1.pdf", original_filename: "attention-v1.pdf", file_hash: sha256:<full hex digest>, verdict: "same arXiv ID (v1); kept latest version"}
```

Every relation edge carries a one-line `why` justification grounded in the paper.

`duplicates` is optional and only present on entries that are the kept version of at least one duplicate. Recording the duplicate's hash also preserves provenance and suppresses re-detection if the same file is dropped into `C/papers/` again.

## refs.yaml entry schema (ghost tier)

`C/refs.yaml` is machine truth for ghosts — referenced but NOT held, non-grounded, never citable on their own. Gitignored like `C/index.yaml`.

```yaml
- key: 2019-lee-foundational-benchmark     # YYYY-firstauthor-short-title (slug-shaped); frozen once assigned
  title: "A Large-Scale Benchmark for Representation Learning"
  authors: ["Lee, Kim"]
  year: 2019
  venue: null                              # best-effort via Crossref/arXiv enrichment
  ids: {doi: null, arxiv: null}            # best-effort via Crossref/arXiv (above-threshold ghosts only)
  cited_by: [2023-smith-contrastive-distillation, 2021-doe-simclr-v3]
  why: "the benchmark dataset much of the corpus trains and evaluates on"
  status: candidate                        # candidate (≥2 citers) | pinned (foundational singleton) | rejected
  note: null                               # required reason when pinned or rejected
```

`count = len(cited_by)`, always derived — never hand-authored. Only held papers contribute to `cited_by`. Ghosts are cited in prose as `⟨ghost:key⟩` and never ground a claim about their own content. The `why`, and any enriched `title`/`venue`/`ids`, are identity and decision-support only — they never ground a content claim about the ghost (that answer is always "not in your papers (referenced only)").

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

Cards are the ROUTING layer. They must never be the final grounding for a specific claim — full text in `C/text/<slug>.md` is.
