# Test suite for YAML configuration validation.
# Framework: pytest
import os
import re
import sys
from pathlib import Path

import pytest

try:
    import yaml
    from yaml.constructor import ConstructorError
except ImportError:
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[1]

def find_yaml_files(limit=2000):
    exts = (".yml", ".yaml")
    files = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_file() and p.suffix in exts:
            # Skip typical build/vendor dirs
            if any(seg in {"node_modules", "dist", "build", ".venv", ".tox", ".eggs", ".git"} for seg in p.parts):
                continue
            files.append(p)
            if len(files) >= limit:
                break
    return files

@pytest.mark.skipif(yaml is None, reason="PyYAML not installed in environment")
def test_all_yaml_files_parse_safely():
    errors = []
    for y in find_yaml_files():
        try:
            with y.open("r", encoding="utf-8") as fh:
                yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            errors.append((str(y), exc))
    if errors:
        pytest.fail("YAML parse errors:\n" + "\n".join(f"- {p}: {e}" for p, e in errors))

class UniqueKeyLoader(yaml.SafeLoader):
    pass

def _mapping_constructor(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise ConstructorError(  # noqa
            "while constructing a mapping",
            node.start_mark,
            "expected a mapping",
            node.start_mark,
        )
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(  # noqa
                "while constructing a mapping",
                key_node.start_mark,
                f"found duplicate key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping

if yaml is not None:
    UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_constructor)

@pytest.mark.skipif(yaml is None, reason="PyYAML not installed in environment")
def test_no_duplicate_keys_across_yaml():
    dups = []
    for y in find_yaml_files():
        try:
            with y.open("r", encoding="utf-8") as fh:
                yaml.load(fh, Loader=UniqueKeyLoader)
        except ConstructorError as ce:
            dups.append((str(y), str(ce)))
        except yaml.YAMLError:
            # Skip files that are not mapping-based or include anchors causing unrelated errors
            pass
    if dups:
        pytest.fail("Duplicate YAML keys found:\n" + "\n".join(f"- {p}: {msg}" for p, msg in dups))

URL_KEY_RE = re.compile(r"(?:^|_|-)(url|uri)(?:$|_|-)", re.I)
COLOR_KEY_RE = re.compile(r"(?:^|_|-)(color|colour|bg|background|fg|foreground)(?:$|_|-)", re.I)
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

@pytest.mark.skipif(yaml is None, reason="PyYAML not installed in environment")
def test_common_value_formats_in_yaml():
    bad_urls = []
    bad_colors = []
    for y in find_yaml_files():
        try:
            data = yaml.safe_load(y.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if data is None:
            continue
        # Traverse for URL/color validations
        def traverse(d, base="", file_path=y):
            if isinstance(d, dict):
                for k, v in d.items():
                    key = str(k)
                    p = f"{base}.{key}" if base else key
                    if isinstance(v, (dict, list)):
                        traverse(v, p)
                    else:
                        if URL_KEY_RE.search(key):
                            s = str(v)
                            if not (s.startswith("http://") or s.startswith("https://")):
                                bad_urls.append((str(file_path), p, s))
                        if COLOR_KEY_RE.search(key):
                            s = str(v)
                            if not HEX_COLOR_RE.match(s):
                                bad_colors.append((str(file_path), p, s))
            elif isinstance(d, list):
                for i, v in enumerate(d):
                    traverse(v, f"{base}[{i}]")
        traverse(data)
    if bad_urls:
        pytest.fail("Invalid URL-like values:\n" + "\n".join(f"- {f} :: {p} = {v}" for f, p, v in bad_urls))
    if bad_colors:
        pytest.fail("Invalid color-like values (expect #RGB or #RRGGBB):\n" + "\n".join(f"- {f} :: {p} = {v}" for f, p, v in bad_colors))

@pytest.mark.skipif(yaml is None, reason="PyYAML not installed in environment")
def test_list_of_objects_have_consistent_keys():
    offenses = []
    def check_list(lst, file_path, base):
        dict_items = [x for x in lst if isinstance(x, dict)]
        if len(dict_items) < 2:
            return
        key_sets = [tuple(sorted(d.keys())) for d in dict_items]
        first = key_sets[0]
        for idx, ks in enumerate(key_sets[1:], start=1):
            if ks != first:
                offenses.append((str(file_path), base, first, ks, idx))
    for y in find_yaml_files():
        try:
            data = yaml.safe_load(y.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        def walk(node, base="", file_path=y):
            if isinstance(node, list):
                check_list(node, file_path, base or "<root>")
                for i, v in enumerate(node):
                    walk(v, f"{base}[{i}]")
            elif isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f"{base}.{k}" if base else str(k))
        walk(data)
    if offenses:
        pytest.fail("Inconsistent object keys in lists:\n" + "\n".join(
            f"- {f} :: {base} expected keys {exp} but saw {ks} at index {idx}"
            for f, base, exp, ks, idx in offenses
        ))

@pytest.mark.skipif(yaml is None, reason="PyYAML not installed in environment")
def test_changed_yaml_files_are_valid_and_have_required_keys():
    """
    Focus on PR diff: validate YAML files changed in this branch have essential keys where applicable.
    Heuristics:
      - If top-level is mapping and contains any of: name, version, description => require name and version non-empty.
      - If contains a top-level list of dicts under keys like 'rules', 'tasks', 'items' => require each item has 'id' and 'title' (if present).
    """
    changed = []
    # Best-effort git-based detection; falls back to all YAMLs if git unavailable
    try:
        import subprocess
        import shutil
        git_cmd = shutil.which("git")
        candidates = []
        if git_cmd:
            # try multiple bases
            for base in ["origin/main", "origin/master", "main", "master"]:
                try:
                    out = subprocess.check_output(  # noqa
                        [git_cmd, "diff", "--name-only", f"{base}...HEAD", "--", "*.yml", "*.yaml"],
                        text=True,
                    )
                    candidates.extend([ln.strip() for ln in out.splitlines() if ln.strip()])
                    if candidates:
                        break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            if not candidates:
                # Last commit fallback
                try:
                    out = subprocess.check_output(  # noqa
                        [git_cmd, "diff", "--name-only", "HEAD~1..HEAD", "--", "*.yml", "*.yaml"],
                        text=True,
                    )
                    candidates = [ln.strip() for ln in out.splitlines() if ln.strip()]
                except (subprocess.CalledProcessError, FileNotFoundError):
                    candidates = []
        changed = [REPO_ROOT / c for c in candidates if (REPO_ROOT / c).exists()]
    except (ImportError, subprocess.CalledProcessError, FileNotFoundError):
        changed = []
    target_files = changed or find_yaml_files()
    issues = []
    for y in target_files:
        try:
            data = yaml.safe_load(y.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            issues.append((str(y), f"parse error: {exc}"))
            continue
        if isinstance(data, dict):
            keys = set(map(str, data.keys()))
            if {"name", "version"} & keys or {"name", "description"} & keys:
                name = str(data.get("name", "")).strip()
                version = str(data.get("version", "")).strip()
                if not name:
                    issues.append((str(y), "missing or empty 'name'"))
                if not version:
                    issues.append((str(y), "missing or empty 'version'"))
            # Check for collections that should have id/title
            for collection_key in ("rules", "tasks", "items"):
                items = data.get(collection_key)
                if isinstance(items, list):
                    for idx, item in enumerate(items):
                        if isinstance(item, dict):
                            if "id" in item or "title" in item or "name" in item:
                                if not str(item.get("id", "")).strip():
                                    issues.append((str(y), f"{collection_key}[{idx}] missing or empty 'id'"))
                                title = str(item.get("title", item.get("name", ""))).strip()
                                if not title:
                                    issues.append((str(y), f"{collection_key}[{idx}] missing or empty 'title'/'name'"))
        # If it's a list at root, ensure elements are homogenous dicts with consistent keys
        if isinstance(data, list):
            dicts = [x for x in data if isinstance(x, dict)]
            if dicts:
                base_keys = set(dicts[0].keys())
                for i, d in enumerate(dicts[1:], start=1):
                    if set(d.keys()) != base_keys:
                        issues.append((str(y), f"list item {i} keys differ from first: {set(d.keys())} != {base_keys}"))
    if issues:
        pytest.fail("Changed YAML validation issues:\n" + "\n".join(f"- {p}: {msg}" for p, msg in issues))

@pytest.mark.skipif(yaml is None, reason="PyYAML not installed in environment")
def test_yaml_anchors_and_aliases_resolve():
    """
    Ensure YAML anchors and aliases do not create unresolved references in changed files.
    """
    target_files = find_yaml_files()
    failures = []
    for y in target_files:
        try:
            # Load once; PyYAML resolves anchors/aliases during construction
            data = yaml.safe_load(y.read_text(encoding="utf-8"))
            _ = data  # unused
        except yaml.YAMLError as exc:
            # Skip files already covered by parse tests; only list anchor-related messages here
            msg = str(exc).lower()
            if "anchor" in msg or "alias" in msg or "recursive" in msg:
                failures.append((str(y), exc))
    if failures:
        pytest.fail("Anchor/Alias issues detected:\n" + "\n".join(f"- {p}: {e}" for p, e in failures))

@pytest.mark.skipif(yaml is None, reason="PyYAML not installed in environment")
def test_env_var_placeholders_are_not_left_unresolved():
    """
    Validate that common environment placeholders are either templated safely or clearly marked.
    Flags entries like ${VAR} without defaults (e.g., ${VAR:-default})
    """
    pattern = re.compile(r"\$\{[A-Z0-9_]+\}")
    offenders = []
    for y in find_yaml_files():
        try:
            text = y.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in pattern.finditer(text):
            token = m.group(0)
            # allow forms like ${VAR:-default} or ${VAR:?err}
            if ":-" in token or ":?" in token:
                continue
            offenders.append((str(y), token))
    if offenders:
        pytest.fail("Unresolved env placeholders without defaults found:\n" + "\n".join(f"- {p}: {tok}" for p, tok in offenders))