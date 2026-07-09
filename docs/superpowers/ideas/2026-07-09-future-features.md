# Future features — parking lot

**Status:** ideas only — NOT designed, NOT approved. Each needs its own brainstorming → spec → plan cycle before implementation.
**Captured:** 2026-07-09 (deferred while finishing the multi-corpus workspace restructure).

These build on the multi-corpus layout (`corpora/<name>/`, one active corpus per session). Revisit when ready.

---

## 1. Conversation capture ("Q&A mode")

**The idea.** When the researcher is in question-answering mode, sessions are automatically saved as transcripts to disk, so the researcher can re-read past Q&A later.

**Hard rule (the firewall).** Saved transcripts are **write-only from the agent's side** — the agent appends to them but **never loads them back into its context**. They are a human-readable archive for the researcher only, never a grounding or routing source. This mirrors the existing grounding firewall ("only full text grounds") and must be encoded in `CLAUDE.md`, not left implicit in a folder convention. A transcript is not corpus evidence; it is a log.

**Why.** A research corpus accretes valuable Q&A over time (what was asked, what the grounded answer was). Losing that to ephemeral chat is wasteful; re-feeding it to the model would corrupt grounding (answers citing past answers instead of papers). Write-only capture keeps the value without the contamination.

**Open design questions (unresolved):**
- **Location.** A Q&A session is always inside one active corpus, so transcripts most likely live **per-corpus** — e.g. `corpora/<active>/conversations/YYYY-MM-DD-*.md` — not a global root folder. (This is why the root `synthesis/` WIP folder was intentionally left undecided during the multi-corpus restructure.) Confirm per-corpus vs. global.
- **Trigger.** What defines "Q&A mode"? Every session? A `/qa` toggle? Auto-detect question turns? Relates to the broader "modes" concept in idea #2.
- **Format.** Plain Markdown transcript (question, grounded answer, citations)? Include the `[slug, §]` citations so the archive stays checkable?
- **Enforcement.** How is "never re-load" guaranteed — a `CLAUDE.md` hard rule + the transcripts living somewhere the routing tiers never read? Confirm the tiers (LANDSCAPE → index → cards → text) explicitly exclude the conversations folder.
- **Gitignore.** Transcripts are corpus-derived → gitignored like the rest of `corpora/`. (Already covered by `corpora/*` once they live per-corpus.)

---

## 2. Python for token efficiency (offload deterministic work)

**The idea.** Move mechanical, deterministic computation **out of the model's context and into scripts**, so tokens are spent on judgment, not bookkeeping. Includes a "modes" notion (distinct operating modes with different tool/permission profiles) and other work Claude currently computes by hand.

**Why.** Today nearly everything the workspace "computes" is done by the LLM reading files and reasoning — including work that is purely mechanical, token-expensive, non-reproducible run-to-run, and occasionally wrong (miscounts, formatting drift). Scripts do that class of work cheaply, deterministically, and correctly.

**Highest-value candidates (from the earlier shell-vs-Python analysis):**
- **View generation** — render `INDEX.md`, `LANDSCAPE.md`, and the ghost promotion table deterministically from `index.yaml` + `refs.yaml`. Pure data→Markdown; the LLM is wasteful and inconsistent at it. *Highest value, lowest cost.* Honest to the "generated — do not edit by hand" banner.
- **Ghost aggregation/selection** — `count = len(cited_by)`, the `≥2` threshold, cross-paper grouping. Exact-threshold logic that gates the promotion shortlist; an LLM miscount silently corrupts the ranking. *Accuracy/trust win, not just efficiency.*
- **Reference / metadata parsing (GROBID / anystyle / refextract)** — the biggest *accuracy* win for bibliography + metadata extraction, but the biggest complexity cost (GROBID is a Java service). The "when accuracy bites / ~300 papers" escalation, alongside embeddings.

**Leave to the LLM (do NOT script):** summaries, card writing, tagging, thematic clustering, the `LANDSCAPE` narrative, relation `why` justifications, dedup nuance, and answering questions. That is the product.

**The tension to weigh:** the project's pitch is "no app, no database, no embeddings — plain files, one dependency (`pdftotext`)." Any Python moves the install surface from one binary to a runtime + deps. Decide deliberately: a stdlib-light view/ghost-count generator (PyYAML) is the highest-leverage first step; GROBID is a later, heavier escalation.

**"Modes" (needs its own definition):** the user raised "modes" in the same breath. Likely candidates: a Q&A/read mode (idea #1) vs. an ingest/sync mode vs. an admin mode, each with different behavior and possibly different permission profiles. Define what modes exist, how they're entered, and what each changes before building.

---

**Next step when revisited:** brainstorm each separately (they interact via "modes" but are independently shippable). Idea #1 (capture) is smaller and corpus-scoped; idea #2 (Python) is a deliberate ethos trade-off — start with the view/ghost-count generator if pursued.
