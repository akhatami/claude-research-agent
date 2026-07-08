# Ghost References Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimalistic, non-grounded "ghost" tier that surfaces papers referenced in held papers' bibliographies as ranked promotion candidates in `LANDSCAPE.md`.

**Architecture:** No new program — the deliverable is edits to the workspace's instruction/convention files. A new `refs.yaml` (machine truth for ghosts, gitignored like `index.yaml`) is produced by a new `/sync` **Phase 5** that parses held papers' bibliographies, merges references across papers, applies a hybrid selection rule, and renders ghosts into `LANDSCAPE.md`. Ghosts are firewalled from grounding via a distinct `⟨ghost:key⟩` citation marker defined in `CLAUDE.md`.

**Tech Stack:** Markdown (all instruction files), YAML (`refs.yaml` schema), Bash + `git` (verification), `pdftotext` output already cached in `text/` (bibliography source). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-08-ghost-references-design.md`

## Global Constraints

- Ghosts are **non-grounded** and never citable on their own; any claim about a ghost's *own* content → **"not in your papers (referenced only)."**
- Citation markers: held papers `[slug]` / `[slug, §X]`; ghosts `⟨ghost:key⟩`.
- Ghost `key` format = `YYYY-firstauthor-short-title` (same shape as a held slug), frozen once assigned.
- Selection (hybrid): a reference becomes a ghost iff `count = len(cited_by) ≥ 2`, **or** it is `status: pinned`; exclude any `status: rejected`. Only **held** papers contribute to `cited_by`.
- Sources: **only** held papers' own bibliographies (`text/<slug>.md`). No external citation-graph discovery; no auto-downloading ghost PDFs.
- Ambiguous cross-paper reference match → **do not merge** (two near-duplicate ghosts beats one wrong merge).
- A reference that resolves to a held `slug` is a normal `relations:` edge, **not** a ghost.
- `refs.yaml` is machine truth, gitignored like `index.yaml`; `count` is always derived, never hand-authored.
- `INDEX.md` stays **held-papers-only**; ghosts appear only in `LANDSCAPE.md`.
- Harvest is folded into `/sync` (Phase 5) — no separate command. Nothing is ever deleted; ghost operations never touch `papers/`, `text/`, or held `index.yaml` entries.

---

### Task 1: `.gitignore` — keep `refs.yaml` local

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Produces: git-ignore behavior so the corpus-derived `refs.yaml` (created in Task 3 / Task 5) is never committed — matching how `index.yaml` is treated.

- [ ] **Step 1: Confirm `refs.yaml` is not yet ignored (failing check)**

Run:
```bash
touch refs.yaml && git check-ignore refs.yaml; echo "exit=$?"; rm -f refs.yaml
```
Expected: no output, then `exit=1` (not currently ignored).

- [ ] **Step 2: Add `refs.yaml` to `.gitignore`**

Use Edit on `.gitignore`:
- old_string:
```
index.yaml
INDEX.md
LANDSCAPE.md
```
- new_string:
```
index.yaml
refs.yaml
INDEX.md
LANDSCAPE.md
```

- [ ] **Step 3: Verify `refs.yaml` is now ignored**

Run:
```bash
touch refs.yaml && git check-ignore refs.yaml; echo "exit=$?"
git status --porcelain | grep refs.yaml; echo "status_exit=$?"
rm -f refs.yaml
```
Expected: `refs.yaml` printed then `exit=0`; the second grep prints nothing then `status_exit=1` (ignored, so not shown by status).

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "feat: gitignore refs.yaml (ghost tier stays local)"
```

---

### Task 2: `CLAUDE.md` — ghost firewall (routing tier, grounding rule, marker)

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: the ghost concept and `refs.yaml` (ignored in Task 1).
- Produces: the behavioral contract every session loads — the `⟨ghost:key⟩` marker and the "ghosts route, never ground" rule that Task 3's skill and Task 5's Q&A rely on. The marker string `⟨ghost:` and file name `refs.yaml` must match Task 3 exactly.

- [ ] **Step 1: Add a "Ghost papers" section after "Grounding and citations"**

Use Edit on `CLAUDE.md`. Anchor on the first line of the next section and prepend the new section before it.
- old_string:
```
## Ingestion and file discipline
```
- new_string:
```
## Ghost papers (referenced but not held)

`refs.yaml` holds **ghosts** — papers referenced in your held papers' bibliographies that you do not hold. They complete the `LANDSCAPE.md` map (ranked there as promotion candidates) and are **not grounded**.

- **Ghosts route, they never ground.** A ghost may appear only as the target of a relation asserted by a held paper: "`[2022-shabani-housediffusion-vector-floorplan, §2]` compares against ⟨ghost:2019-wu-rplan⟩" — that sentence is grounded in the held paper's full text. Any claim about a ghost's *own* content ("RPLAN contains 80K plans") is **"not in your papers (referenced only)"** — the same discipline as out-of-corpus knowledge.
- **Distinct citation marker.** Held papers cite as `[slug]`; ghosts cite as `⟨ghost:key⟩`, so a verifiable citation is never confused with a pointer to something you don't hold.
- `refs.yaml` is generated by the `sync` skill (Phase 5) — never hand-edit it.

## Ingestion and file discipline
```

- [ ] **Step 2: Note that `refs.yaml` feeds ghost nodes in the generated views**

Use Edit on `CLAUDE.md`.
- old_string:
```
- `INDEX.md` and `LANDSCAPE.md` are generated from `index.yaml` — never hand-edit them; regenerate via the `sync` skill.
```
- new_string:
```
- `INDEX.md` and `LANDSCAPE.md` are generated from `index.yaml` (with ghost nodes drawn from `refs.yaml`) — never hand-edit them; regenerate via the `sync` skill. `INDEX.md` lists held papers only; ghosts appear only in `LANDSCAPE.md`.
```

- [ ] **Step 3: Verify the anchors landed and are consistent**

Run:
```bash
grep -c "⟨ghost:" CLAUDE.md
grep -c "referenced only" CLAUDE.md
grep -c "refs.yaml" CLAUDE.md
```
Expected: each count ≥ 1 (marker present, firewall phrase present, refs.yaml referenced).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: CLAUDE.md — ghost firewall (route-not-ground, ⟨ghost:key⟩ marker)"
```

---

### Task 3: `/sync` skill — `refs.yaml` schema, Phase 5 harvest, promotion, render

**Files:**
- Modify: `.claude/skills/sync/SKILL.md`

**Interfaces:**
- Consumes: the `⟨ghost:key⟩` marker and firewall rules from Task 2; `refs.yaml` ignored in Task 1; held `text/<slug>.md` bibliographies.
- Produces: the harvest procedure and `refs.yaml` schema that Task 5 exercises. Field names other tasks rely on: `key`, `title`, `authors`, `year`, `ids`, `cited_by` (list of held slugs), `why`, `status` (`candidate|pinned|rejected`), `note`. Ghost Mermaid node id convention: `ghost_<key>`.

- [ ] **Step 1: Advertise ghost harvesting in the skill description (frontmatter)**

Use Edit on `.claude/skills/sync/SKILL.md`.
- old_string:
```
update index.yaml, and regenerate INDEX.md and LANDSCAPE.md. Use when the session-start hook reports new papers or the user asks to sync/organize the corpus.
```
- new_string:
```
update index.yaml, harvest referenced-but-not-held ghost papers into refs.yaml, and regenerate INDEX.md and LANDSCAPE.md. Use when the session-start hook reports new papers or the user asks to sync/organize the corpus.
```

- [ ] **Step 2: Add promotion handling to the Phase 2 dry-run**

Use Edit on `.claude/skills/sync/SKILL.md`.
- old_string:
```
| `smith_preprint.pdf` | move | `_duplicates/smith_preprint.pdf` | duplicate of 2023-smith-… (arXiv id match) |

Include uncertain dedupe cases as explicit questions. **Wait for approval. Do not touch files before it.**
```
- new_string:
```
| `smith_preprint.pdf` | move | `_duplicates/smith_preprint.pdf` | duplicate of 2023-smith-… (arXiv id match) |
| `Wu_RPLAN_2019.pdf` | rename + promote | `papers/2019-wu-rplan.pdf` | promotes ⟨ghost:2019-wu-rplan⟩ → held paper |

Include uncertain dedupe cases as explicit questions. If a new PDF matches an existing ghost in `refs.yaml` (shared DOI/arXiv, or fuzzy title + first-author), present it as a **promotion**: on approval it is ingested as a normal held paper, and Phase 5 then removes its ghost entry and turns its former `cited_by` papers into inbound `relations:`. **Wait for approval. Do not touch files before it.**
```

- [ ] **Step 3: Extend Phase 4 with ghost rendering (held-only INDEX, ghost table + dashed nodes in LANDSCAPE)**

Use Edit on `.claude/skills/sync/SKILL.md`.
- old_string:
```
## Phase 4 — Regenerate

1. **`INDEX.md`** — generated table over all `index.yaml` entries, sorted by year desc: `| slug | title | year | venue | tags | one-line summary | status |`. Header note: "Generated from index.yaml — do not edit by hand."
2. **`LANDSCAPE.md`** — the corpus story, regenerated from `index.yaml` + cards:
   - Thematic clusters (from tags/relations): what each cluster is trying to solve, which papers belong, how clusters connect, and where the open tensions/gaps are. Narrative prose, not bullets-only.
   - A Mermaid `graph TD` of relations: nodes are slugs, edges labeled with the relation type. Same generated-file header note.
3. Report orphans and any `needs-ocr` / `metadata-unverified` statuses in the final summary to the user.
```
- new_string:
```
## Phase 4 — Regenerate

1. **`INDEX.md`** — generated table over all `index.yaml` entries (held papers only — ghosts never appear here), sorted by year desc: `| slug | title | year | venue | tags | one-line summary | status |`. Header note: "Generated from index.yaml — do not edit by hand."
2. **`LANDSCAPE.md`** — the corpus story, regenerated from `index.yaml` + cards + `refs.yaml`:
   - Thematic clusters (from tags/relations): what each cluster is trying to solve, which papers belong, how clusters connect, and where the open tensions/gaps are. Narrative prose, not bullets-only.
   - A Mermaid `graph TD` of relations: held nodes are slugs, edges labeled with the relation type. Draw each ghost as a node with id `ghost_<key>` styled distinctly (dashed border, dimmed) via a `classDef ghost`, with an edge from each citing held paper labeled `references`. Same generated-file header note.
   - **Ghost papers — referenced but not held (promotion candidates)** (from `refs.yaml`): a table sorted by pull (co-citation `count`) descending — `| ghost | year | pull | cited by | why |`. This is the promotion shortlist; the ghosts whose absence most weakens the corpus sit at the top.
3. Report orphans and any `needs-ocr` / `metadata-unverified` statuses in the final summary to the user.
```

- [ ] **Step 4: Insert the new "Phase 5 — Harvest ghosts" section before the schema block**

Use Edit on `.claude/skills/sync/SKILL.md`. Anchor on the schema heading and prepend Phase 5 before it.
- old_string:
```
## index.yaml entry schema
```
- new_string:
```
## Phase 5 — Harvest ghosts (referenced-but-not-held papers)

Runs after Phase 4 on every sync. Produces/updates `refs.yaml` and the ghost surfaces in `LANDSCAPE.md`. Ghosts are sourced ONLY from held papers' own bibliographies — no external lookup for discovery.

1. **Extract bibliographies:** for each held paper, take the References/Bibliography section from `text/<slug>.md` (the tail after the last "References"/"Bibliography" heading).
2. **Parse & normalize** each reference entry → first-author surname, year, title fragment, DOI/arXiv id if present. Bibliographies from `status: needs-ocr` papers may be garbled — best-effort only.
3. **Resolve against held papers first:** if a reference matches an existing `index.yaml` slug (shared DOI/arXiv, or fuzzy title + first-author), it is a normal `relations:` edge, NOT a ghost — drop it from the ghost pass.
4. **Match/merge across papers:** group references that are the same work — exact by shared DOI/arXiv, else fuzzy on first-author + year + title. When a match is ambiguous, DO NOT merge (two near-duplicate ghosts is a smaller harm than a wrong merge). Each surviving group gets a `cited_by` list of the held slugs that reference it.
5. **Select (hybrid):** keep a group as a ghost iff `len(cited_by) ≥ 2`, OR it is carried forward as `status: pinned`. Exclude any group whose key is `status: rejected`. Non-pinned singletons are excluded.
6. **Assign keys & reconcile with existing `refs.yaml`:**
   - New ghost → `key` = `YYYY-firstauthor-short-title` (same shape as a slug), frozen once assigned.
   - Existing ghost → preserve its `key`, `status`, and `note`; refresh `cited_by` and enriched fields.
   - **Promotion:** if a ghost now matches a paper newly held after this sync's Phase 3, remove it from `refs.yaml` (it has graduated) and add the held papers in its former `cited_by` as inbound `relations:` on the promoted paper's `index.yaml` entry.
7. **Enrich (best-effort, above-threshold ghosts only):** verify metadata via Crossref/arXiv exactly as Phase 1 does, filling `venue`/`ids`. Offline or no confident match → leave best-effort `title`/`year` with `ids: null`; retried on later syncs.
8. **Write `refs.yaml`** (schema below) and render the ghost surfaces in `LANDSCAPE.md` per Phase 4.

Curation verdicts persist across syncs: a ghost the user dismisses is recorded `status: rejected` with a `note` and never re-surfaces; a foundational singleton the agent keeps is `status: pinned` with a `note` reason.

## index.yaml entry schema
```

- [ ] **Step 5: Insert the `refs.yaml` schema before the card template**

Use Edit on `.claude/skills/sync/SKILL.md`. Anchor on the card-template heading and prepend the schema before it. (The block below contains a fenced YAML example; paste it exactly, inner fences included.)
- old_string:
```
## Card template — notes/<slug>.md
```
- new_string (paste verbatim, including the ```yaml fence):

````
## refs.yaml entry schema (ghost tier)

`refs.yaml` is machine truth for ghosts — referenced but NOT held, non-grounded, never citable on their own. Gitignored like `index.yaml`.

```yaml
- key: 2019-wu-rplan                       # YYYY-firstauthor-short-title (slug-shaped); frozen once assigned
  title: "Data-driven Interior Plan Generation for Residential Buildings"
  authors: ["Wu, Wenming"]
  year: 2019
  ids: {doi: null, arxiv: null}            # best-effort via Crossref/arXiv (above-threshold ghosts only)
  cited_by: [2022-shabani-housediffusion-vector-floorplan, 2025-hu-gsdiff-structural-graph-floorplan-diffusion]
  why: "RPLAN — the benchmark dataset much of the corpus trains on"
  status: candidate                        # candidate (≥2 citers) | pinned (foundational singleton) | rejected
  note: null                               # required reason when pinned or rejected
```

`count = len(cited_by)`, always derived — never hand-authored. Only held papers contribute to `cited_by`. Ghosts are cited in prose as `⟨ghost:key⟩` and never ground a claim about their own content.

## Card template — notes/<slug>.md
````

- [ ] **Step 6: Verify all inserts landed and stayed consistent**

Run:
```bash
grep -c "name: sync" .claude/skills/sync/SKILL.md
grep -c "Phase 5 — Harvest ghosts" .claude/skills/sync/SKILL.md
grep -c "refs.yaml entry schema" .claude/skills/sync/SKILL.md
grep -c "⟨ghost:2019-wu-rplan⟩" .claude/skills/sync/SKILL.md
grep -c "rename + promote" .claude/skills/sync/SKILL.md
grep -c "ghost_<key>" .claude/skills/sync/SKILL.md
grep -c "cited_by:" .claude/skills/sync/SKILL.md
```
Expected: every count ≥ 1 (frontmatter intact; Phase 5, schema, marker, promotion row, ghost-node convention, and `cited_by` field all present).

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/sync/SKILL.md
git commit -m "feat: /sync Phase 5 — harvest ghosts, promotion, refs.yaml schema, render"
```

---

### Task 4: `README.md` — document the ghost tier

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above; documents the ghost feature for a fresh user.

- [ ] **Step 1: Add a "Maps the neighborhood" item to "What it does"**

Use Edit on `README.md`. Anchor on the existing item 2 and append item 3 after it.
- old_string:
```
2. **Answers questions grounded in YOUR papers,** with checkable citations (`[slug, §5.2]` + direct quotes), starting broad and drilling into fewer papers as you go deeper. If your papers don't cover it, it says so.
```
- new_string:
```
2. **Answers questions grounded in YOUR papers,** with checkable citations (`[slug, §5.2]` + direct quotes), starting broad and drilling into fewer papers as you go deeper. If your papers don't cover it, it says so.
3. **Maps the neighborhood:** surfaces papers your held papers cite but you don't have yet as *ghosts* in `LANDSCAPE.md`, ranked by how many of your papers reference each one — a ready-made shortlist of what to add next. Ghosts enrich the map but are never cited as grounding; drop a ghost's PDF into `papers/` and the next sync promotes it to a full paper.
```

- [ ] **Step 2: Verify**

Run:
```bash
grep -c "ghost" README.md
```
Expected: ≥ 1.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README — ghost tier (referenced-but-not-held promotion candidates)"
```

---

### Task 5: Live acceptance on the real 20-paper corpus

**Files:**
- No machinery changes unless the run surfaces a bug (then fix the relevant instruction file and commit `fix:`). The corpus outputs (`refs.yaml`, `LANDSCAPE.md`) are gitignored — nothing to commit for them.

**Interfaces:**
- Consumes: all previous tasks, run against the existing `papers/`, `text/`, `index.yaml`.

- [ ] **Step 1: Run the harvest**

Run the `sync` skill in-session (no new PDFs, so this exercises Phase 4–5 regeneration over the existing corpus). Then confirm the ghost store exists and is populated:
```bash
test -f refs.yaml && echo "refs.yaml exists"
grep -c "cited_by:" refs.yaml
```
Expected: `refs.yaml exists`; `cited_by:` count ≥ 1. Ghosts should plausibly include the corpus's shared foundations (e.g. RPLAN, House-GAN) with multi-paper `cited_by` lists.

- [ ] **Step 2: Verify the selection rule and no self-ghosts (agent check)**

Read `refs.yaml` and `index.yaml`. Confirm:
- Every ghost has either `len(cited_by) ≥ 2` or `status: pinned`; no non-pinned singletons.
- No ghost `key` equals any held `slug` in `index.yaml` (a held-paper→held-paper citation must be a `relations:` edge, not a ghost).

Quick shell aid (should print nothing — no key collides with a held slug):
```bash
comm -12 \
  <(grep -E '^[[:space:]]*-?[[:space:]]*key:' refs.yaml | sed -E 's/.*key:[[:space:]]*//' | sort -u) \
  <(grep -E '^[[:space:]]*-?[[:space:]]*slug:' index.yaml | sed -E 's/.*slug:[[:space:]]*//' | sort -u)
echo "collision_exit=$?"
```
Expected: no output (empty intersection). (POSIX classes used because macOS `sed`/`grep` don't support `\s`.)

- [ ] **Step 3: Verify the LANDSCAPE surfaces**

```bash
grep -c "Ghost papers — referenced but not held" LANDSCAPE.md
grep -c "classDef ghost" LANDSCAPE.md
grep -c "ghost_" LANDSCAPE.md
```
Expected: each ≥ 1 (promotion-candidates table present; ghost nodes styled and drawn in the Mermaid graph). Also eyeball the table: sorted by pull descending.

- [ ] **Step 4: Verify the grounding firewall (agent Q&A)**

Ask two questions in-session and confirm behavior:
- "What dataset does RPLAN contain / how many plans?" → answer must be **"not in your papers (referenced only)"** (or equivalent), NOT a fabricated figure.
- "Which of my held papers build on RPLAN?" → answered from the ghost's `cited_by`, citing held papers as `[slug]`, and referring to the ghost as `⟨ghost:2019-wu-rplan⟩` (or its actual key).

- [ ] **Step 5: Verify `reject` persistence**

Pick a low-value ghost. Instruct the agent to reject it; confirm its `refs.yaml` entry becomes `status: rejected` with a `note`. Re-run the `sync` skill and confirm it does NOT reappear in the promotion-candidates table.

- [ ] **Step 6 (optional): Verify promotion dry-run**

If a ghost's PDF is freely obtainable (e.g. an arXiv-available reference), download it into `papers/`, run the `sync` skill, and confirm Phase 2 offers a **rename + promote** row for it. On approval, confirm it becomes a held `slug`, leaves `refs.yaml`, and its former citers appear as inbound `relations:` on the new entry. If no ghost PDF is freely obtainable, skip and note it — promotion mechanics are also covered by the Task 3 dry-run text.

- [ ] **Step 7: Confirm no corpus-derived files got staged**

```bash
git status --porcelain | grep -E 'refs\.yaml|LANDSCAPE\.md|index\.yaml'; echo "exit=$?"
```
Expected: no output, then `exit=1` (all three are gitignored). If the run surfaced a bug you fixed in an instruction file, that fix is committed separately as `fix:`; the corpus outputs remain local.
