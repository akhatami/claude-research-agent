import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import generate_views as gv  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    return os.path.join(FIX, name)


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
        with open(fixture("expected_INDEX.md"), encoding="utf-8") as f:
            expected = f.read()
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
        with open(fixture("expected_ghosts.md"), encoding="utf-8") as f:
            expected = f.read().rstrip("\n")
        self.assertEqual(gv.render_ghost_table(selected), expected)

    def test_empty_ghosts_message(self):
        self.assertEqual(gv.render_ghost_table([]), "No ghost papers yet.")


class GraphTests(unittest.TestCase):
    def test_render_graph_matches_golden(self):
        entries = gv.load_yaml(fixture("index.yaml"), default=[])
        ghosts = gv.select_ghosts(gv.load_yaml(fixture("refs.yaml"), default=[]))
        with open(fixture("expected_graph.md"), encoding="utf-8") as f:
            expected = f.read().rstrip("\n")
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


if __name__ == "__main__":
    unittest.main()
