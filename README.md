# Claude Research Agent

A replicable [Claude Code](https://claude.com/claude-code) workspace that turns a folder of paper PDFs into an organized, queryable research corpus. No app, no database, no embeddings — plain files plus agent conventions.

**What it does**

1. **Organizes:** dedupes, renames each paper once to a stable `YYYY-firstauthor-short-title` slug, extracts a text cache, writes a structured card per paper, and maintains `index.yaml` (machine truth) → generated `INDEX.md` (overview table) and `LANDSCAPE.md` (the story of your corpus + a Mermaid relation graph).
2. **Answers questions grounded in YOUR papers,** with checkable citations (`[slug, §5.2]` + direct quotes), starting broad and drilling into fewer papers as you go deeper. If your papers don't cover it, it says so.
3. **Maps the neighborhood:** surfaces papers your held papers cite but you don't have yet as *ghosts* in `LANDSCAPE.md`, ranked by how many of your papers reference each one — a ready-made shortlist of what to add next. Ghosts enrich the map but are never cited as grounding; drop a ghost's PDF into `papers/` and the next sync promotes it to a full paper.

**Requirements**

- Claude Code
- `pdftotext` from poppler: `brew install poppler` (macOS) / `apt install poppler-utils` (Linux)

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
