import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import generate_views as gv  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    return os.path.join(FIX, name)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class LoadValidateTests(unittest.TestCase):
    def test_load_index_fixture(self):
        entries = gv.load_yaml(fixture("index.yaml"), default=[])
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["slug"], "2023-smith-contrastive-distillation")

    def test_missing_file_returns_default(self):
        self.assertEqual(gv.load_yaml(fixture("does-not-exist.yaml"), default=[]), [])

    def test_dependency_error_when_yaml_missing(self):
        saved = gv.yaml
        gv.yaml = None
        try:
            with self.assertRaises(gv.DependencyError):
                gv.load_yaml(fixture("index.yaml"))
        finally:
            gv.yaml = saved

    def test_validate_entries_missing_slug(self):
        with self.assertRaises(gv.DataError):
            gv.validate_entries([{"title": "x", "year": 2020}])

    def test_validate_ghosts_missing_key(self):
        with self.assertRaises(gv.DataError):
            gv.validate_ghosts([{"title": "x"}])


class RenderIndexTests(unittest.TestCase):
    def test_render_index_matches_golden(self):
        entries = gv.load_yaml(fixture("index.yaml"), default=[])
        expected = read_text(fixture("expected_INDEX.md"))
        self.assertEqual(gv.render_index(entries), expected)

    def test_escape_cell_pipes(self):
        self.assertEqual(gv.escape_cell("a|b"), "a\\|b")


class GhostTests(unittest.TestCase):
    def setUp(self):
        self.ghosts = gv.load_yaml(fixture("refs.yaml"), default=[])

    def test_select_applies_threshold_and_status(self):
        keys = [g["key"] for g in gv.select_ghosts(self.ghosts)]
        # 2019-lee (pull 2) kept; 2018-kim (pinned singleton) kept;
        # 2015-old-singleton (pull 1, candidate) dropped; 2017-generic-ml (rejected) dropped.
        self.assertEqual(keys, ["2019-lee-benchmark", "2018-kim-foundational"])

    def test_render_ghost_table_matches_golden(self):
        selected = gv.select_ghosts(self.ghosts)
        expected = read_text(fixture("expected_ghosts.md")).rstrip("\n")
        self.assertEqual(gv.render_ghost_table(selected), expected)

    def test_empty_ghosts_message(self):
        self.assertEqual(gv.render_ghost_table([]), "No ghost papers yet.")


class GraphTests(unittest.TestCase):
    def test_render_graph_matches_golden(self):
        entries = gv.load_yaml(fixture("index.yaml"), default=[])
        ghosts = gv.select_ghosts(gv.load_yaml(fixture("refs.yaml"), default=[]))
        expected = read_text(fixture("expected_graph.md")).rstrip("\n")
        self.assertEqual(gv.render_graph(entries, ghosts), expected)

    def test_node_ids_are_hyphen_free(self):
        self.assertEqual(gv.node_id("2021-doe-simclr"), "n_2021_doe_simclr")
        self.assertEqual(gv.ghost_node_id("2019-lee-benchmark"), "ghost_2019_lee_benchmark")

    def test_graph_without_ghosts_has_no_classdef(self):
        entries = gv.load_yaml(fixture("index.yaml"), default=[])
        out = gv.render_graph(entries, [])
        self.assertNotIn("classDef ghost", out)


class RegionTests(unittest.TestCase):
    def test_replace_existing_region_preserves_surroundings(self):
        text = (
            "# Title\n\nNarrative stays.\n\n"
            "<!-- BEGIN GENERATED:graph -->\nold\n<!-- END GENERATED:graph -->\n\nAfter.\n"
        )
        out, appended = gv.replace_region(text, "graph", "NEW")
        self.assertFalse(appended)
        self.assertIn("Narrative stays.", out)
        self.assertIn("After.", out)
        self.assertIn(
            "<!-- BEGIN GENERATED:graph -->\nNEW\n<!-- END GENERATED:graph -->", out
        )
        self.assertNotIn("old", out)

    def test_missing_region_is_appended_and_flagged(self):
        text = "# Title\n\nNarrative only.\n"
        out, appended = gv.replace_region(text, "ghosts", "TBL")
        self.assertTrue(appended)
        self.assertIn("Narrative only.", out)
        self.assertIn(
            "<!-- BEGIN GENERATED:ghosts -->\nTBL\n<!-- END GENERATED:ghosts -->", out
        )

    def test_unterminated_region_raises(self):
        text = "<!-- BEGIN GENERATED:graph -->\nno end marker\n"
        with self.assertRaises(gv.DataError):
            gv.replace_region(text, "graph", "X")


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copy(fixture("index.yaml"), os.path.join(self.tmp, "index.yaml"))
        shutil.copy(fixture("refs.yaml"), os.path.join(self.tmp, "refs.yaml"))

    def _seed_landscape(self, with_ghosts_fence=True):
        parts = [
            "# Corpus landscape\n\n## The story of this corpus\n\n",
            "Two papers form a contrastive-learning cluster.\n\n",
            "<!-- BEGIN GENERATED:graph -->\nstale\n<!-- END GENERATED:graph -->\n\n",
        ]
        if with_ghosts_fence:
            parts.append("<!-- BEGIN GENERATED:ghosts -->\nstale\n<!-- END GENERATED:ghosts -->\n")
        with open(os.path.join(self.tmp, "LANDSCAPE.md"), "w", encoding="utf-8") as f:
            f.write("".join(parts))

    def test_generate_writes_index_and_regions(self):
        self._seed_landscape()
        warnings = gv.generate(self.tmp)
        self.assertEqual(warnings, [])
        self.assertEqual(
            read_text(os.path.join(self.tmp, "INDEX.md")),
            read_text(fixture("expected_INDEX.md")),
        )
        land = read_text(os.path.join(self.tmp, "LANDSCAPE.md"))
        self.assertIn("Two papers form a contrastive-learning cluster.", land)
        self.assertIn("graph TD", land)
        self.assertIn("2019-lee-benchmark", land)
        self.assertNotIn("stale", land)

    def test_generate_is_idempotent(self):
        self._seed_landscape()
        gv.generate(self.tmp)
        first_index = read_text(os.path.join(self.tmp, "INDEX.md"))
        first_land = read_text(os.path.join(self.tmp, "LANDSCAPE.md"))
        gv.generate(self.tmp)
        self.assertEqual(read_text(os.path.join(self.tmp, "INDEX.md")), first_index)
        self.assertEqual(read_text(os.path.join(self.tmp, "LANDSCAPE.md")), first_land)

    def test_missing_ghosts_fence_self_heals(self):
        self._seed_landscape(with_ghosts_fence=False)
        warnings = gv.generate(self.tmp)
        self.assertEqual(warnings, ["ghosts"])

    def test_malformed_yaml_writes_nothing(self):
        # Unterminated double-quoted scalar → a real YAML parse error → DataError.
        with open(os.path.join(self.tmp, "index.yaml"), "w", encoding="utf-8") as f:
            f.write('- slug: x\n  title: "unterminated\n')
        self._seed_landscape()
        rc = gv.main(["generate_views.py", self.tmp])
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "INDEX.md")))

    def test_main_usage_error(self):
        self.assertEqual(gv.main(["generate_views.py"]), 2)


class StressGraphTests(unittest.TestCase):
    """Guards the graph's edge filters and node cap against silent regression."""

    def setUp(self):
        self.entries = gv.load_yaml(fixture("stress_index.yaml"), default=[])
        self.selected = gv.select_ghosts(gv.load_yaml(fixture("stress_refs.yaml"), default=[]))
        self.out = gv.render_graph(self.entries, self.selected)

    def test_ghost_nodes_capped_at_limit(self):
        # 10 ghosts selected; only the top GHOST_GRAPH_LIMIT get drawn.
        node_lines = [l for l in self.out.splitlines() if '["⟨ghost⟩' in l]
        self.assertEqual(len(node_lines), gv.GHOST_GRAPH_LIMIT)
        self.assertIn(gv.ghost_node_id("2010-aaa-cap4"), self.out)   # highest pull, kept
        self.assertNotIn(gv.ghost_node_id("2010-f07"), self.out)     # over the cap, dropped
        self.assertNotIn(gv.ghost_node_id("2010-f08"), self.out)

    def test_relation_to_non_held_target_is_dropped(self):
        self.assertIn(
            "%s -->|builds-on| %s" % (gv.node_id("2022-alpha"), gv.node_id("2021-beta")),
            self.out,
        )
        # 3000-phantom is not a held paper → no node, no edge.
        self.assertNotIn("3000-phantom", self.out)
        self.assertNotIn(gv.node_id("3000-phantom"), self.out)

    def test_non_held_citer_is_dropped(self):
        gid = gv.ghost_node_id("2010-aab-nonheld")
        self.assertIn("%s -. references .-> %s" % (gv.node_id("2022-alpha"), gid), self.out)
        self.assertIn("%s -. references .-> %s" % (gv.node_id("2021-beta"), gid), self.out)
        # ext-outsider cites the ghost but is not held → no edge.
        self.assertNotIn("ext-outsider", self.out)

    def test_held_citer_edges_capped_at_three(self):
        gid = gv.ghost_node_id("2010-aaa-cap4")
        ref_edges = [l for l in self.out.splitlines() if l.strip().endswith("-> %s" % gid)]
        self.assertEqual(len(ref_edges), 3)
        # Citers drawn in slug order: delta, gamma, beta; alpha (4th) is cut.
        self.assertIn("%s -. references .-> %s" % (gv.node_id("2019-delta"), gid), self.out)
        self.assertNotIn("%s -. references .-> %s" % (gv.node_id("2022-alpha"), gid), self.out)


if __name__ == "__main__":
    unittest.main()
