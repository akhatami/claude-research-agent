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


if __name__ == "__main__":
    unittest.main()
