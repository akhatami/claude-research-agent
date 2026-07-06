---
name: sync
description: Ingest new or changed PDFs in papers/ — extract text, verify metadata, dedupe, rename once (after dry-run approval), write per-paper cards, update index.yaml, and regenerate INDEX.md and LANDSCAPE.md. Use when the session-start hook reports new papers or the user asks to sync/organize the corpus.
---

# /sync — corpus ingestion and regeneration

Incremental by design: a PDF is "new" iff its sha256 does not appear in `index.yaml`. On each sync, also re-attempt metadata verification for entries with `status: metadata-unverified`, updating them to `ok` on success. Also report **orphans** (index entries whose PDF no longer exists in `papers/` or `_duplicates/`) — report only, never auto-remove.

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

1. Rename PDF to `papers/<slug>.pdf` (this is the ONLY time this file is ever renamed) or move duplicate to `_duplicates/` (keep its original name there). When moving a duplicate, record the verdict in the KEEPER's `index.yaml` entry under its `duplicates:` list (schema below) — recording the hash preserves provenance and suppresses re-detection if the same file is dropped into `papers/` again.
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
  duplicates:
    - {file: "_duplicates/attention-v1.pdf", original_filename: "attention-v1.pdf", file_hash: sha256:<full hex digest>, verdict: "same arXiv ID (v1); kept latest version"}
```

Every relation edge carries a one-line `why` justification grounded in the paper.

`duplicates` is optional and only present on entries that are the kept version of at least one duplicate. Recording the duplicate's hash also preserves provenance and suppresses re-detection if the same file is dropped into `papers/` again.

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
