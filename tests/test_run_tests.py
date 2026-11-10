"""The parallel test runner runs every discovered test once and fails on any failure or import error."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_tests  # noqa: E402

PASSING = """
import unittest
class A(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.ready = True
    def test_one(self): self.assertTrue(self.ready)
    def test_two(self): self.assertTrue(self.ready)
class B(unittest.TestCase):
    def test_three(self): pass
    @unittest.skip('fixture')
    def test_skipped(self): pass
"""


class RunnerTests(unittest.TestCase):
    def suite(self, files):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name, text in files.items():
            (directory / name).write_text(textwrap.dedent(text))
        return directory

    def run_main(self, directory, jobs=2):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = run_tests.main(["-j", str(jobs), "-s", str(directory)])
        return code, output.getvalue()

    def test_every_test_runs_once_across_workers(self):
        directory = self.suite({"test_pass.py": PASSING, "test_more.py": "import unittest\nclass C(unittest.TestCase):\n    def test_four(self): pass\n"})
        code, output = self.run_main(directory)
        self.assertEqual(code, 0, output)
        self.assertIn("Running 5 tests in 3 units with 2 workers", output)
        self.assertIn("Ran 5 tests in ", output)
        self.assertTrue(output.rstrip().endswith("OK"))

    def test_a_failing_test_fails_the_run(self):
        directory = self.suite({"test_pass_b.py": PASSING, "test_fail.py": "import unittest\nclass F(unittest.TestCase):\n    def test_bad(self): self.fail('boom')\n"})
        code, output = self.run_main(directory)
        self.assertEqual(code, 1)
        self.assertIn("FAILED: test_fail.F", output)
        self.assertIn("AssertionError: boom", output)

    def test_an_import_error_fails_before_running(self):
        directory = self.suite({"test_pass_c.py": PASSING, "test_broken.py": "import missing_module_for_this_test\n"})
        code, output = self.run_main(directory)
        self.assertEqual(code, 1)
        self.assertIn("Test discovery failed", output)
        self.assertNotIn("Running ", output)

    def test_no_tests_fails(self):
        code, output = self.run_main(self.suite({"helper.py": "VALUE = 1\n"}))
        self.assertEqual(code, 1)
        self.assertIn("No tests discovered", output)

    def test_slow_classes_run_first_in_interleaved_slices(self):
        ids = [f"test_site.Pages.test_{index:02d}" for index in range(10)] + ["test_fast.Fast.test_a", "test_fast.Fast.test_b"]
        units = run_tests.plan(ids, {"test_site"})
        self.assertEqual(len(units), 1 + -(-10 // run_tests.SLICE_METHODS))
        self.assertEqual(units[-1], ["test_fast.Fast.test_a", "test_fast.Fast.test_b"])
        self.assertEqual(sorted(test for unit in units for test in unit), sorted(ids))
        self.assertEqual(units[0][:2], ["test_site.Pages.test_00", f"test_site.Pages.test_{-(-10 // run_tests.SLICE_METHODS):02d}"])


if __name__ == "__main__":
    unittest.main()
