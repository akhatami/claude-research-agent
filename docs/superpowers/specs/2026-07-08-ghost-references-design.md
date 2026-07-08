# Ghost References — Design

**Date:** 2026-07-08
**Status:** Awaiting user approval
**Extends:** [2026-07-06-research-assistant-workspace-design.md](2026-07-06-research-assistant-workspace-design.md)

## What this is

A minimalistic second tier for the research workspace: **ghosts** — papers that are *referenced in the bibliographies of papers you already hold, but that you do not hold yourself*. Their only job is to make `LANDSCAPE.md` a more complete map — to show the foundational works the corpus stands on (datasets, seminal methods, lineage) that are currently invisible because the graph can only draw edges between the 20 held papers.

Ghosts are **not grounded** and are **never citable on their own**. They are surfaced as ranked **promotion candidates** so the user can decide, at a glance, which referenced papers are worth actually obtaining and ingesting.

**Scope target:** a self-limiting set (estimated ~15–40 ghosts for the current corpus), sourced *only* from held papers' own reference lists. Explicitly out of scope: external citation-graph discovery (Semantic Scholar etc.), auto-downloading ghost PDFs, perfect bibliographic parsing.

## Core principle: the grounding firewall

The workspace's load-bearing rule is **cards and index may *route*; only full text may *ground*.** Ghosts extend this with a sharp, safe boundary:

- ✅ **Groundable** — a ghost as the *target of a relation asserted by a held paper*:
  "`[2022-shabani-housediffusion, §2]` compares against ⟨ghost:2019-wu-rplan⟩."
  This sentence is grounded in Shabani's full text (which you hold); the ghost is just the edge's endpoint.
- ❌ **Not groundable** — any claim about a ghost's *own* content:
  "RPLAN contains 80K plans" → the required answer is **"not in your papers (referenced only)."**

A ghost is grounded only as *"a reference made, and characterized, by a paper you hold"* — never as an independent source. This preserves the "answers cite papers verifiably" guarantee completely.

**Distinct citation marker.** Held papers cite as `[slug, §5.2]`. Ghosts cite as `⟨ghost:key⟩` — visually unmistakable and greppable, so a reader never confuses a verifiable citation with a pointer to something the corpus does not hold.

## Identity and the two-tier trust boundary

The tiers are physically separated so the file layout mirrors the trust boundary:

| tier | store | citable? | identifier |
|---|---|---|---|
| **held** (existing) | `index.yaml` | yes — grounded in `text/<slug>.md` | `slug` (`YYYY-firstauthor-short-title`, frozen forever) |
| **ghost** (new) | `refs.yaml` | no — referenced only | `key` (`YYYY-firstauthor-short-title` — same pattern as a slug) |

**`index.yaml` = citable. `refs.yaml` = not.** A ghost `key` is assigned once and preserved across re-harvests (matched by DOI/arXiv/fuzzy-title), because user verdicts (`pinned`/`rejected`) reference it and must survive regeneration. It deliberately uses the same shape as a held `slug`, so a promoted ghost's `key` becomes its `slug` with no transform.

## refs.yaml — ghost machine truth

New file, sibling to `index.yaml`, gitignored the same way (it is corpus-derived). One entry per ghost:

```yaml
# Ghost tier — referenced but NOT held. Non-grounded, never citable on its own.
# Generated/maintained by /sync Phase 5. Do not hand-edit counts.
- key: 2019-wu-rplan                       # YYYY-firstauthor-short-title (slug-shaped); frozen once assigned
  title: "Data-driven Interior Plan Generation for Residential Buildings"
  authors: ["Wu, Wenming", "..."]
  year: 2019
  ids: {doi: null, arxiv: null}            # best-effort, filled via existing Crossref/arXiv verify
  cited_by: [2022-shabani-housediffusion-vector-floorplan,
             2025-hu-gsdiff-structural-graph-floorplan-diffusion,
             2026-klimenko-hypergraphformer-llm-floorplan]   # the fact; count = len(cited_by)
  why: "RPLAN — the benchmark dataset much of the corpus trains on"
  status: candidate                        # candidate | pinned | rejected
  note: null                               # required reason when pinned or rejected
```

**The count is always derived** (`count = len(cited_by)`), never authored. Storing the citer list rather than an integer is what keeps it from drifting, and it doubles as decision-support: *who* pulls a ghost in (one cluster vs. across clusters) is itself a signal.

Only **held** papers contribute to `cited_by` — ghosts have no bibliography, because their full text is not held.

## Selection rule (hybrid)

A reference becomes a ghost iff:

- **`count ≥ 2`** — cited by two or more held papers (automatic, objective, self-limiting); **or**
- **`status: pinned`** — a foundational singleton the agent flags (e.g. the original diffusion paper, cited once but underpinning a whole cluster). Pins are recorded with a `note` reason and shown as "pinned" in the surfaced table; the user may `reject` any they disagree with.

Excluded: singletons that are not pinned, and any `key` marked `rejected`.

## /sync — new Phase 5: Harvest ghosts

Runs after the existing Phase 4 (Regenerate), on every sync, keyed to whether the held set changed.

1. **Extract** the References/Bibliography section from each held `text/<slug>.md`.
2. **Normalize** each reference entry → first-author surname, year, title fragment, DOI/arXiv if present.
3. **Resolve against held papers first** — if a reference *is* a corpus paper (matches a `slug`), it is a normal `relations:` edge in `index.yaml`, **not** a ghost.
4. **Match/merge** remaining references across papers: DOI/arXiv exact match; else fuzzy on author + year + title. Build each surviving reference's `cited_by` list.
5. **Select (hybrid):** keep `count ≥ 2`; carry forward `pinned` singletons; drop `rejected` keys.
6. **Reconcile** with existing `refs.yaml`: preserve `key`s and `pinned`/`rejected` verdicts, refresh `cited_by`/counts, and **detect promotions** (a ref that now matches a newly-held `slug` leaves `refs.yaml`).
7. **Enrich** (best-effort, above-threshold ghosts only): reuse the existing Crossref/arXiv verification to fill `venue`/`ids`. Offline → leave best-effort fields; no blocking.
8. **Render** the surfaces (below).

Bibliographies from `needs-ocr` papers may be garbled; references sourced only from such text are best-effort and the noise is tolerated (coarse matching + user curation is the correction loop, not parser perfection).

## Surfacing — where the user decides what to promote

- **`LANDSCAPE.md`** gains a **"Ghost papers — referenced but not held (promotion candidates)"** section: a table sorted by pull (count) descending —
  `| ghost | year | pull | cited by | why |`. Read top-down = the promotion shortlist; the ghosts whose absence most weakens the corpus sit at the top.
- **Mermaid graph:** ghost nodes rendered in a distinct style (dashed border / dimmed) so they are visibly the map's *inbound roads*, clearly separated from held nodes.
- **`INDEX.md`:** unchanged — stays **held-papers-only**. It is the citable overview table; keeping ghosts out of it preserves the firewall. (Ghosts live only in the map, `LANDSCAPE.md`.)

## Lifecycle

```
        (auto, count ≥ 2)                      (agent flags singleton, with reason)
  reference ───────────────▶ candidate        singleton ──────────▶ pinned
                                  │                                     │
             user: "not relevant" │                                     │ user disagrees
                                  ▼                                     ▼
                               rejected  ◀──────────────────────────────┘
                              (persisted; excluded on future syncs)

  candidate/pinned ── user drops PDF in papers/ ──▶ PROMOTED
     → new-PDF hook detects it → /sync Phase 2 dry-run confirms
       "this PDF matches ⟨ghost:key⟩ → promote"
     → graduates to a held paper in index.yaml; leaves refs.yaml
     → its cited_by edges become real inbound relations on the new slug
```

- **reject** — user tells the agent a ghost is not worth holding; agent sets `status: rejected` with a `note`. Future syncs never re-surface it. Mirrors how dedupe verdicts persist today.
- **pin** — agent-proposed foundational singleton, recorded with reason; user retains control via `reject`.
- **promote** — the escape hatch to full grounding: dropping the PDF into `papers/` routes through the *existing* detection hook and `/sync` dry-run. Promotion is confirmed in the Phase 2 approval table alongside rename/dedupe verdicts, so nothing graduates silently.

## Files touched (all additive — nothing deleted)

| file | change |
|---|---|
| `refs.yaml` | **new** — ghost machine truth; gitignored like `index.yaml` |
| `.claude/skills/sync/SKILL.md` | add Phase 5 (harvest), `refs.yaml` schema, promotion detection in Phase 2 dry-run, ghost render rules for Phase 4 |
| `CLAUDE.md` | ghost firewall rules, `⟨ghost:key⟩` marker, `refs.yaml` as a routing-only tier in tiered routing |
| `.gitignore` | add `refs.yaml` |
| `README.md` | move the ghost tier from "not in v1" to shipped; one-line description |

The SessionStart hook (`detect-new-papers.sh`) needs **no change** — promotion reuses its existing new-PDF detection.

## Error handling

- **Garbled bibliography** (`needs-ocr` source) → best-effort extraction; noisy ghosts corrected by user `pin`/`reject`, never blocking a sync.
- **Ambiguous cross-paper match** → err toward *not* merging (two near-duplicate ghosts is a smaller harm than a wrong merge); user can reject the spurious one.
- **Reference is actually a held paper** → resolved to a `relations:` edge, never a ghost (Phase 5 step 3).
- **Offline during enrichment** → ghost keeps best-effort `title`/`year`; `ids`/`venue` left null, re-attempted on later syncs.
- **Nothing destructive** — ghosts are additive and regenerable; no ghost operation ever touches `papers/`, `text/`, or held entries.

## Testing / acceptance

Verified by exercising the real flow on the current 20-paper corpus:

1. Run `/sync` → Phase 5 produces `refs.yaml` with ≥2-cited references (expect RPLAN, House-GAN, etc.), each with a correct `cited_by` list and `count = len(cited_by)`.
2. `LANDSCAPE.md` shows the promotion-candidate table sorted by pull descending, and the Mermaid graph renders ghost nodes distinctly.
3. A held paper citing another held paper produces a `relations:` edge, **not** a ghost (no self-referential ghosts).
4. Ask "what does RPLAN contain?" → answer is "not in your papers (referenced only)"; ask "which held papers build on RPLAN?" → answered from `cited_by` with held `[slug]` citations.
5. `reject` a ghost → it disappears and does not reappear on the next `/sync`.
6. Drop a ghost's real PDF into `papers/` → Phase 2 dry-run offers promotion → on approval it becomes a held `slug`, leaves `refs.yaml`, and its former citers appear as real inbound relations.

## Explicitly cut (YAGNI)

External citation-graph APIs; auto-downloading ghost PDFs; ghost-to-ghost citation edges (no ghost full text to parse); perfect bibliographic parsing; a separate `/ghosts` command (harvest is folded into `/sync` to keep the surface minimal); ghosts in `INDEX.md`.
