from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from lfortran_bench.adapters import _run_command


class RunCommandTests(unittest.TestCase):
    def test_successful_command_returns_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_command(
                [sys.executable, "-c", "print('done')"],
                Path(tmp),
                timeout_seconds=5,
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "done")

    def test_timeout_kills_process_that_ignores_sigterm(self) -> None:
        code = (
            "import signal, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "time.sleep(30)"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_command(
                [sys.executable, "-c", code],
                Path(tmp),
                timeout_seconds=1,
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.returncode, 124)
        self.assertIn("timed out", result.error or "")


if __name__ == "__main__":
    unittest.main()
