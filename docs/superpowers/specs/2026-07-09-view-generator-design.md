# Deterministic View & Ghost-Count Generator — Design

**Date:** 2026-07-09
**Status:** Awaiting user approval
**Parked ideas source:** [../ideas/2026-07-09-future-features.md](../ideas/2026-07-09-future-features.md) (idea #2, first slice)

## What this is

Today every generated view is written by the LLM. On each `/sync`, Phase 4 has the model hand-render `INDEX.md` (a pure table) and `LANDSCAPE.md`, and Phase 5 has it hand-compute ghost counts, apply the `≥2` threshold, sort by pull, and render the promotion table and the Mermaid graph. All of it is mechanical, token-expensive as *output* (the costly kind, regenerated in full every sync), non-reproducible run-to-run, and occasionally wrong — an LLM miscount silently corrupts the ghost ranking.

This moves that mechanical class of work into a small Python generator, `scripts/generate_views.py`. The script owns everything derivable from `index.yaml` + `refs.yaml`; the LLM keeps everything that is judgment. The result is deterministic, unit-testable views and an honest "generated — do not edit" banner, at zero model-output cost for the mechanical content.

**Scope target:** the highest-leverage, lowest-cost slice of the "Python offload" idea. Explicitly *not* in scope this cycle: GROBID/reference-parsing, embeddings, and the "modes" concept — each gets its own brainstorm → spec → plan cycle.

## Decisions settled in brainstorming

1. **Scope** — the view + ghost-count generator only. GROBID and "modes" stay parked.
2. **Dependency** — `python3` + PyYAML, one `pip install`. `index.yaml`/`refs.yaml` stay YAML (human-readable, comments intact). The script is *the* renderer — not an optional accelerator with an LLM fallback, so there is exactly one renderer to maintain and the generated banner is always true. Both `pdftotext` and this generator are ingestion-time tools; **asking questions still needs nothing but the files.**
3. **LANDSCAPE composition** — one `LANDSCAPE.md`. The script owns fenced regions (HTML-comment markers) and rewrites only those in place; the LLM narrative between them is untouched. Keeping the relation graph *inline* with the narrative is a deliberate benefit, not a tolerated cost: every Tier-0 read pulls the corpus's story and its structure into context together, which improves routing and grounding.

## Ownership boundary

The cut follows one rule: **the script owns everything mechanical and derivable; the LLM owns everything that is judgment.**

### Script owns (deterministic, from `index.yaml` + `refs.yaml`)

- **`INDEX.md`** — the whole file: generated banner + a table over held papers only (ghosts never appear here), sorted `year` desc then `slug` asc. Columns: `slug | title | year | venue | tags | one-line summary | status`.
- **`LANDSCAPE.md` generated regions** — the Mermaid relation graph (held papers + top-8 ghosts by pull) and the ghost-promotion table.
- **All ghost arithmetic** — `count = len(cited_by)`, the selection filter (`count ≥ 2` **or** `status: pinned`, excluding `status: rejected`), sort-by-pull, and the top-8 graph pick.

### LLM owns (judgment)

- **`index.yaml` / `refs.yaml` content** — summaries, tags, relations and their `why`, and ghost **grouping** (fuzzy-matching references into one ghost, building `cited_by`, setting curation `status`/`note`). Grouping is dedup nuance and stays with the LLM.
- **`LANDSCAPE.md` narrative region** — thematic clusters, the corpus story, tensions/gaps.
- **The cards** (`notes/<slug>.md`).

### `refs.yaml` semantics change (required by this design)

Today Phase 5 applies the `≥2` threshold *while writing* `refs.yaml`, so sub-threshold singletons are never stored. To genuinely move the threshold to the script (the accuracy goal — no LLM arithmetic touches the ranking), `refs.yaml` now stores **all grouped candidates, including sub-threshold singletons**, each with `cited_by` and curation `status`. The script applies the filter at render time.

Clean split that results:
- `refs.yaml` = the raw harvested-candidate store (the LLM's grouping + curation).
- The *view* (which ghosts appear, in what order) = 100% script-derived.

Consequence for Phase 5's "enrich above-threshold ghosts only": the LLM may still count informally to pick enrichment targets (non-authoritative; enrichment is best-effort and retried on later syncs), while the script remains the sole authority for the table and graph.

## The generator script

**Location & invocation.** One file, `scripts/generate_views.py` — committed machinery (only `corpora/*` and `synthesis/*` are gitignored, so `scripts/` ships with the template). It takes the corpus directory as an **explicit argument**, never reading `.active-corpus` itself:

```
python3 scripts/generate_views.py corpora/<active>
```

Explicit-arg keeps it testable — point it at a fixture corpus, no global state. The sync skill passes the active corpus path.

**Inputs → outputs.**
- Reads: `<corpus>/index.yaml`, `<corpus>/refs.yaml`.
- Writes `<corpus>/INDEX.md` — the whole file (banner + table).
- Rewrites **only the fenced regions** of `<corpus>/LANDSCAPE.md` in place, byte-preserving everything outside them.

**Marker mechanism.** Two generated regions in `LANDSCAPE.md`, each an HTML-comment fence:

```
<!-- BEGIN GENERATED:graph -->
```mermaid
graph TD
    …
```
<!-- END GENERATED:graph -->

<!-- BEGIN GENERATED:ghosts -->
| ghost | year | pull | status | cited by | why |
| … |
<!-- END GENERATED:ghosts -->
```

The script reads the file, replaces the text *between* each marker pair, and leaves the narrative untouched. `INDEX.md` needs no markers — it is whole-file-owned, so a header banner suffices.

**Graph region contents** (mirrors current Phase 4/5 output, now deterministic):
- Mermaid `graph TD` over held papers: hyphen-free node ids, edges labeled with the relation `type`.
- Top-8 ghosts by pull drawn as `ghost_<key>` nodes (hyphens → underscores), styled via a single `classDef ghost` (dashed, dimmed), each with `references` edges from up to 3 of its citing held papers. The ghost *table* lists all ghosts; only the top 8 are drawn.

**Ghost-table region contents:** section heading **Ghost papers — referenced but not held (promotion candidates)**, table sorted by pull desc then key asc, columns `ghost | year | pull | status | cited by | why`, `status` showing `candidate` or `pinned`.

**Determinism (the whole point).** Every ordering has an explicit total sort key, so re-running on unchanged YAML yields **byte-identical** output:
- INDEX rows: `year` desc, then `slug` asc.
- Ghost table / graph pick: `pull` desc, then `key` asc; take top 8 for the graph.
- `cited_by` lists rendered sorted.
- No wall-clock timestamps in output (they would break idempotence). Stdlib + PyYAML only.

## Sync skill integration & ordering

The generator runs **once, last** — after both YAML files are final, because the graph draws ghost nodes and the ghost table needs `refs.yaml`. Phase changes to `.claude/skills/sync/SKILL.md`:

- **Phase 3 (execute)** — unchanged. The LLM writes `index.yaml` entries, the text cache, and cards.
- **Phase 4 (regenerate)** — shrinks to judgment only: the LLM authors the **LANDSCAPE narrative region**. It no longer hand-writes `INDEX.md`, the graph, or the ghost table. On a brand-new corpus it creates `LANDSCAPE.md` from a skeleton (narrative header + the two empty marker fences) the SKILL provides.
- **Phase 5 (ghost harvest)** — unchanged in spirit, but now writes **all grouped candidates** (including sub-threshold singletons) to `refs.yaml` with `cited_by` + `status`. No threshold is applied here anymore.
- **Phase 6 (generate — new, terminal)** — run `python3 scripts/generate_views.py corpora/<active>`. Produces `INDEX.md` whole and fills both LANDSCAPE fences. The sync summary reports what it wrote.

**Bootstrap / self-heal.** If a marker fence is absent (new corpus, or a hand-mangled file), the generator appends the filled fence and warns on stderr rather than failing — so ordering between "LLM wrote narrative" and "generator ran" never deadlocks. A missing `LANDSCAPE.md` is created with the narrative header + both filled fences.

**Doc updates in scope.**
- `CLAUDE.md` and `SKILL.md` lines that call `INDEX.md`/`LANDSCAPE.md` "generated" become fully honest, and name the fenced regions for `LANDSCAPE.md` (narrative = LLM, fences = script). The Phase 4/5 prose is rewritten to the flow above.
- `SKILL.md` `refs.yaml` schema note updated: stores all candidates incl. singletons; threshold is applied by the generator, not here.
- `README.md` Requirements gains "ingestion also needs `python3` + `pyyaml`"; the "Not in v1" Python-offload line flips to shipped (view + ghost-count generator).

## Migration (one-time, per existing corpus)

Existing corpora already have a hand-rendered graph and ghost table living *un-fenced* inside `LANDSCAPE.md`. If the generator simply self-healed against those files, it would append fenced copies and leave the old ones as orphaned duplicates. So the first run against any pre-existing corpus is a one-time conversion, done by the LLM during the next `/sync` (not by the generator):

1. In `LANDSCAPE.md`, delete the old hand-written Mermaid graph block and the old ghost-promotion table from the narrative body.
2. Insert the two empty marker fences (`graph`, `ghosts`) where they belong.
3. Run the generator (Phase 6), which fills them.

The narrative prose (clusters, story) is preserved verbatim — only the mechanical blocks are excised and handed to the generator. `INDEX.md` needs no conversion; it is overwritten wholesale on first generation. This is a local edit to gitignored corpus data — no history to rewrite, nothing deleted outside the one corpus.

## Error handling (fail-closed)

The script is *the* renderer, so it never silently degrades — it either produces correct views or refuses and says why:

- **PyYAML missing** → exit non-zero with `PyYAML not installed — run \`pip install pyyaml\``. Mirrors the poppler check. Sync surfaces it and stops; there is no fallback to hand-rendering.
- **Malformed YAML / missing required field** (e.g. an entry with no `slug`, or a ghost with no `key`) → fail loudly, naming the offending entry, and **write nothing**. Never emit a half-correct view.
- **`refs.yaml` absent** (corpus with no ghosts yet) → not an error: empty ghost table ("No ghost papers yet."), no ghost nodes in the graph. Same handling for an empty held set.
- **Marker fence missing** → self-heal (append the filled fence) + stderr warning, not a failure.

## Testing (the payoff of determinism)

Deterministic output makes the mechanical layer genuinely unit-testable — the thing the LLM path could never be. All test assets are committed under `scripts/tests/` (outside `corpora/`, so not gitignored):

- **Fixture corpus** — a small `index.yaml` + `refs.yaml` exercising the tricky cases: several held papers, each relation `type`, ghosts above and below threshold, one `pinned` singleton, one `rejected` key, and a `needs-ocr` paper.
- **Golden files** — `expected_INDEX.md` and the expected LANDSCAPE fence contents; tests assert byte-for-byte equality.
- **Behavioral tests** —
  - Idempotence: run twice → identical output.
  - Threshold correctness: sub-threshold singleton excluded, `pinned` singleton kept, `rejected` dropped, counts exact.
  - Fail-closed: malformed YAML → non-zero exit and nothing written.
  - Self-heal: a `LANDSCAPE.md` with a missing fence gets it appended; narrative preserved.
- **Runner** — stdlib `unittest` (`python3 -m unittest`), no pytest dependency, to honor the dep-light ethos.

## Success criteria

1. `/sync` produces `INDEX.md`, the LANDSCAPE graph, and the ghost table with **zero** mechanical model-output tokens (the LLM emits only judgment content + narrative).
2. Re-running the generator on unchanged YAML changes nothing (byte-identical).
3. Ghost ranking is correct by construction — counts and thresholds are computed, never hand-tallied.
4. The LANDSCAPE narrative survives every regeneration untouched; only the fences change.
5. A malformed or incomplete YAML fails the sync loudly instead of emitting a wrong view.
6. `python3 -m unittest` passes against the fixture corpus and goldens.

## Explicitly cut (YAGNI / parked)

- **GROBID / anystyle / refextract** reference + metadata parsing — the heavy accuracy escalation; its own later cycle.
- **The "modes" concept** (Q&A vs ingest vs admin, permission profiles) — its own definition and cycle.
- **Embeddings / any semantic layer** — against the project ethos; not this.
- **A `--check`/dry-run flag** — tests cover validation; add only if a real need appears.
- **Scripting any judgment work** — summaries, cards, tagging, clustering, the LANDSCAPE narrative, relation `why`, dedup/ghost grouping, and question answering all stay with the LLM. That is the product.
- **Migrating machine files to JSON** — YAML is kept for readability and comments; PyYAML is the accepted cost.
