"""
Tests for requirements-dev.txt

Framework:
- Uses Python's built-in unittest framework for zero extra dependencies.
- If this repository uses pytest, it will automatically discover and run these
  unittest-style tests as well.

Focus:
- This suite validates the contents and structure of requirements-dev.txt,
  emphasizing correctness and maintainability that are typically affected by PR diffs:
  * file exists and has meaningful content
  * no duplicate package entries (case- and hyphen/underscore-insensitive)
  * -r/--requirement inclusions reference existing files
  * no exact duplicate lines (ignoring surrounding whitespace)
  * no trailing whitespace on lines
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


# ---------------------------
# Helper utilities (test-only)
# ---------------------------

REQ_FILE_NAME = "requirements-dev.txt"


def find_upwards(filename: str, start: Optional[Path] = None) -> Optional[Path]:
    """
    Search upwards from 'start' (or this test file) to locate 'filename'.
    Returns a Path if found, else None.
    """
    if start is None:
        start = Path(__file__).resolve().parent
    for p in [start, *start.parents]:
        candidate = p / filename
        if candidate.exists():
            return candidate
    return None


def iter_lines(path: Path) -> Iterable[Tuple[int, str, str]]:
    """
    Yield (line_no, raw_line, stripped_line) for each line in the file.
    Keeps original raw_line to detect trailing whitespace and duplicates.
    """
    with path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            yield i, raw, raw.strip()


def classify_line(stripped: str) -> str:
    """
    Rough classification of a requirements line.
    - 'comment': blank or comment
    - 'include': -r/--requirement or -c/--constraint (we treat both as references)
    - 'option' : other command options (e.g., --index-url)
    - 'req'    : an install requirement (including VCS/URL forms)
    """
    if not stripped or stripped.startswith("#"):
        return "comment"
    # Include/constraint forms
    if stripped.startswith("-r ") or stripped.startswith("--requirement "):
        return "include"
    if stripped.startswith("-c ") or stripped.startswith("--constraint "):
        return "include"
    # Other options
    if stripped.startswith("-") or stripped.startswith("--"):
        return "option"
    return "req"


_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\s*\[.*\])?\s*(?:[<>=!~]{1,2}.*)?$")


def normalize_name(name: str) -> str:
    """
    PEP 503-style normalization: collapse runs of -, _, . to a single dash, and lower-case.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def extract_req_name(stripped: str) -> Optional[str]:
    """
    Attempt to extract a canonical package name from a requirement line.
    - Handles extras (pkg[dev]==1.2.3) and markers (pkg==1.2.3; python_version<'3.12')
    - For VCS/URL lines, attempts to read #egg=name if present.
    Returns normalized name or None if not parseable.
    """
    # Remove inline marker and/or comment fragments for simpler matching
    base = stripped.split(";", 1)[0].split("#", 1)[0].strip()
    m = _NAME_RE.match(base)
    if m:
        return normalize_name(m.group(1))

    # VCS / direct URL with #egg=
    m2 = re.search(r"#egg=([A-Za-z0-9._-]+)", stripped)
    if m2:
        return normalize_name(m2.group(1))
    return None


def extract_included_path(stripped: str) -> Optional[str]:
    """
    If line is an include/constraint (-r/--requirement/-c/--constraint),
    return the referenced path token; else None.
    """
    tokens = stripped.split()
    if not tokens:
        return None
    if tokens[0] in ("-r", "--requirement", "-c", "--constraint"):
        return tokens[1] if len(tokens) > 1 else None
    return None


# ---------------------------
# Test cases
# ---------------------------

class TestRequirementsDev(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.req_path = find_upwards(REQ_FILE_NAME)
        if cls.req_path is None:
            raise unittest.SkipTest(f"{REQ_FILE_NAME} not found in repository tree.")

    def test_file_exists_and_has_meaningful_content(self):
        self.assertTrue(self.req_path.exists(), f"{self.req_path} must exist.")
        lines = list(iter_lines(self.req_path))
        self.assertGreater(len(lines), 0, f"{REQ_FILE_NAME} should not be empty.")

        # Ensure at least one non-comment line present
        any_non_comment = any(classify_line(s) != "comment" for _, _, s in lines)
        self.assertTrue(any_non_comment, f"{REQ_FILE_NAME} must contain at least one non-comment line.")

    def test_no_exact_duplicate_lines_ignoring_whitespace(self):
        seen = set()
        dups = []
        for ln, raw, _ in iter_lines(self.req_path):
            key = raw.strip()
            if not key:
                continue
            if key in seen:
                dups.append((ln, key))
            else:
                seen.add(key)
        self.assertFalse(dups, f"Duplicate requirement lines detected (ignoring whitespace): {dups}")

    def test_no_duplicate_packages_case_insensitive_normalized(self):
        names: List[str] = []
        for _, _, s in iter_lines(self.req_path):
            if classify_line(s) != "req":
                continue
            name = extract_req_name(s)
            # Some 'req' lines may be VCS URLs without #egg=; skip since not extractable
            if name:
                names.append(name)
        dupes = sorted({n for n in names if names.count(n) > 1})
        self.assertFalse(
            dupes,
            f"Duplicate package entries found in {REQ_FILE_NAME} (normalized): {dupes}. "
            f"Merge version constraints or remove duplicates."
        )

    def test_included_files_exist(self):
        base_dir = self.req_path.parent
        missing = []
        for ln, _, s in iter_lines(self.req_path):
            if classify_line(s) != "include":
                continue
            ref = extract_included_path(s)
            # When '-r' is provided without a path: treat as missing
            if not ref:
                missing.append((ln, s, "<missing path>"))
                continue
            ref_path = (base_dir / ref).resolve()
            if not ref_path.exists():
                missing.append((ln, s, str(ref_path)))
        self.assertFalse(
            missing,
            "The following include/constraint lines reference files that do not exist:\n"
            + "\n".join(f"  line {ln}: {content} -> {resolved}" for ln, content, resolved in missing)
        )

    def test_no_trailing_whitespace(self):
        offenders = []
        for ln, raw, _ in iter_lines(self.req_path):
            # Consider the line without the trailing newline
            check = raw[:-1] if raw.endswith("\n") else raw
            if len(check) > 0 and check[-1].isspace():
                offenders.append(ln)
        self.assertFalse(
            offenders,
            f"Trailing whitespace found on lines: {offenders}. "
            f"Please trim spaces at end-of-line for cleaner diffs."
        )


if __name__ == "__main__":
    unittest.main()