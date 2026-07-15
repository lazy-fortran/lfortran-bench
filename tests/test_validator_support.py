from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tasks"))
from validator_support import materialize_fixed_test

from test_core import git, make_fixture_repo


class ValidatorSupportTests(unittest.TestCase):
    def test_materializes_file_from_fixed_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, base, fixed = make_fixture_repo(root)
            git(repo, "checkout", base)
            task_yaml = root / "task.yaml"
            task_yaml.write_text(yaml.safe_dump({"fixed_commit": fixed}))

            destination = materialize_fixed_test(repo, "result.txt", task_yaml)

            self.assertEqual(destination.read_text(), "fixed\n")


if __name__ == "__main__":
    unittest.main()
