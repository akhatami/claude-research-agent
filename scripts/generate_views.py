#!/usr/bin/env python3
"""Generate deterministic corpus views (INDEX.md + LANDSCAPE.md fenced regions)
from index.yaml + refs.yaml.

Spec: docs/superpowers/specs/2026-07-09-view-generator-design.md
"""

import os
import sys

try:
    import yaml
except ImportError:
    yaml = None


class DependencyError(Exception):
    pass


class DataError(Exception):
    pass


def load_yaml(path, default=None):
    if yaml is None:
        raise DependencyError("PyYAML not installed — run `pip install pyyaml`")
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise DataError("%s: invalid YAML — %s" % (path, exc))
    return default if data is None else data


def validate_entries(entries):
    for i, e in enumerate(entries):
        for field in ("slug", "title", "year"):
            if not e.get(field):
                label = e.get("slug") or ("entry #%d" % i)
                raise DataError("index.yaml %s: missing required field '%s'" % (label, field))


def validate_ghosts(ghosts):
    for i, g in enumerate(ghosts):
        if not g.get("key"):
            raise DataError("refs.yaml entry #%d: missing required field 'key'" % i)


INDEX_BANNER = "<!-- Generated from index.yaml — do not edit by hand. -->"

GHOST_HEADING = "## Ghost papers — referenced but not held (promotion candidates)"


def escape_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def pull(ghost):
    return len(ghost.get("cited_by") or [])


def select_ghosts(ghosts):
    kept = [
        g for g in ghosts
        if g.get("status") != "rejected" and (pull(g) >= 2 or g.get("status") == "pinned")
    ]
    return sorted(kept, key=lambda g: (-pull(g), g["key"]))


def render_ghost_table(selected):
    if not selected:
        return "No ghost papers yet."
    lines = [
        GHOST_HEADING,
        "",
        "| ghost | year | pull | status | cited by | why |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for g in selected:
        cited = ", ".join(sorted(g.get("cited_by") or []))
        lines.append("| %s | %s | %d | %s | %s | %s |" % (
            escape_cell(g["key"]),
            escape_cell(g.get("year") or ""),
            pull(g),
            escape_cell(g.get("status") or "candidate"),
            escape_cell(cited),
            escape_cell(g.get("why") or ""),
        ))
    return "\n".join(lines)


def fmt_tags(tags):
    return ", ".join(tags or [])


def render_index(entries):
    rows = sorted(entries, key=lambda e: (-int(e["year"]), e["slug"]))
    lines = [
        INDEX_BANNER,
        "",
        "# Corpus index",
        "",
        "| slug | title | year | venue | tags | summary | status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            escape_cell(e["slug"]),
            escape_cell(e["title"]),
            escape_cell(e["year"]),
            escape_cell(e.get("venue") or ""),
            escape_cell(fmt_tags(e.get("tags"))),
            escape_cell(e.get("summary") or ""),
            escape_cell(e.get("status") or "ok"),
        ))
    return "\n".join(lines) + "\n"


def replace_region(text, name, content):
    begin = "<!-- BEGIN GENERATED:%s -->" % name
    end = "<!-- END GENERATED:%s -->" % name
    block = "%s\n%s\n%s" % (begin, content, end)
    start = text.find(begin)
    if start == -1:
        return text.rstrip("\n") + "\n\n" + block + "\n", True
    stop = text.find(end, start)
    if stop == -1:
        raise DataError("LANDSCAPE.md: region '%s' has BEGIN but no END marker" % name)
    return text[:start] + block + text[stop + len(end):], False


GHOST_GRAPH_LIMIT = 8


def node_id(slug):
    return "n_" + slug.replace("-", "_")


def ghost_node_id(key):
    return "ghost_" + key.replace("-", "_")


def render_graph(entries, selected_ghosts):
    held_slugs = {e["slug"] for e in entries}
    lines = ["```mermaid", "graph TD"]

    for e in sorted(entries, key=lambda e: e["slug"]):
        lines.append('    %s["%s"]' % (node_id(e["slug"]), e["slug"]))

    edges = []
    for e in entries:
        for rel in (e.get("relations") or []):
            to = rel.get("to")
            if to in held_slugs:
                edges.append((e["slug"], to, rel.get("type") or ""))
    for frm, to, typ in sorted(edges):
        lines.append("    %s -->|%s| %s" % (node_id(frm), typ, node_id(to)))

    drawn = sorted(selected_ghosts[:GHOST_GRAPH_LIMIT], key=lambda g: g["key"])
    for g in drawn:
        lines.append('    %s["⟨ghost⟩ %s"]' % (ghost_node_id(g["key"]), g["key"]))
    for g in drawn:
        citers = [c for c in sorted(g.get("cited_by") or []) if c in held_slugs][:3]
        for c in citers:
            lines.append("    %s -. references .-> %s" % (node_id(c), ghost_node_id(g["key"])))
    if drawn:
        lines.append("    classDef ghost stroke-dasharray:5 5,opacity:0.55;")
        ids = ",".join(ghost_node_id(g["key"]) for g in drawn)
        lines.append("    class %s ghost;" % ids)

    lines.append("```")
    return "\n".join(lines)
