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


if __name__ == "__main__":
    unittest.main()
