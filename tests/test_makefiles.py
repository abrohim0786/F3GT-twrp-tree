# Added by PR: Makefile validations
# Test framework: Python unittest (pytest-compatible). Pytest will collect these tests automatically.

import os
import re
import unittest
from pathlib import Path

EXCLUDE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "dist", "build",
    ".tox", ".mypy_cache", ".pytest_cache", "__pycache__"
}

def _find_makefiles(base_dir: Path = Path(".")):
    """Locate Makefile files in the repository, excluding common build/cache dirs."""
    makefiles = []
    for p in base_dir.rglob("Makefile"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        makefiles.append(p)
    # Deduplicate while preserving order
    seen, unique = set(), []
    for p in makefiles:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique

class TestMakefilesBasic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.makefiles = _find_makefiles()

    def setUp(self):
        if not getattr(self, "makefiles", []):
            self.skipTest("No Makefile files found in repository.")

    def test_each_makefile_is_readable_and_nonempty(self):
        """Happy path: every Makefile should exist, be readable, and non-empty."""
        for mf in self.makefiles:
            with self.subTest(makefile=str(mf)):
                self.assertTrue(mf.is_file(), f"{mf} is not a regular file")
                self.assertTrue(os.access(mf, os.R_OK), f"{mf} is not readable")
                self.assertGreater(mf.stat().st_size, 0, f"{mf} is empty")

    def test_each_makefile_contains_meaningful_content(self):
        """
        Edge case coverage: a Makefile with only comments/blank lines provides no value.
        Validate presence of at least one non-comment, non-blank line.
        """
        non_comment_re = re.compile(r"^\\s*(?!#).+\\S")
        for mf in self.makefiles:
            with self.subTest(makefile=str(mf)):
                lines = mf.read_text(encoding="utf-8", errors="ignore").splitlines()
                meaningful = [ln for ln in lines if non_comment_re.match(ln)]
                self.assertTrue(meaningful, f"{mf} appears to contain no non-comment content")