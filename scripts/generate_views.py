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


def escape_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


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
