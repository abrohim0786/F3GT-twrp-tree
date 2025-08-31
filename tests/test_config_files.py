# Test framework: pytest
# ruff: noqa: S101
# These tests validate configuration files (JSON, YAML, TOML, INI, .env) with a focus on files impacted by this PR.
# They are intentionally generic so that changed config files are covered automatically without hard-coding paths.

from __future__ import annotations

import json
import os
import re
from pathlib import Path
import configparser
import importlib
import pytest

# Prefer stdlib tomllib (Py>=3.11); fallback to tomli if available.
try:
    import tomllib as _tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:
    _tomllib = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {
    "node_modules", ".git", "dist", "build", ".venv", "venv", "__pycache__", ".pytest_cache",
    "target", ".tox", ".cache", "coverage", "out"
}

def _is_excluded(p: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in p.parts)

def _rglob_many(patterns: list[str]) -> list[Path]:
    seen: set[Path] = set()
    for pat in patterns:
        for p in REPO_ROOT.rglob(pat):
            if p.is_file() and not _is_excluded(p):
                seen.add(p)
    return sorted(seen)

def load_toml_file(path: Path) -> dict:
    if _tomllib is not None:
        with path.open("rb") as f:
            return _tomllib.load(f)  # type: ignore[attr-defined]
    try:
        tomli = importlib.import_module("tomli")
        with path.open("rb") as f:
            return tomli.load(f)  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        pytest.skip("TOML parser not available (tomllib/tomli).")

def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)

# Collect files by type (auto-discovers changed and existing configs)
JSON_FILES = [p for p in _rglob_many(["*.json"]) if p.name not in {"package-lock.json"}]
YAML_FILES = _rglob_many(["*.yml", "*.yaml"])
TOML_FILES = _rglob_many(["*.toml"])
INI_FILES = _rglob_many(["*.ini", "setup.cfg", "tox.ini", ".editorconfig"])
ENV_FILES = [p for p in _rglob_many([".env", ".env.*", "*.env"]) if p.is_file()]

WORKFLOW_FILES = [p for p in YAML_FILES if ".github" in p.parts and "workflows" in p.parts]
COMPOSE_FILES = [p for p in YAML_FILES if p.name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}]

@pytest.mark.parametrize("path", JSON_FILES, ids=_rel)
def test_json_files_are_valid(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data is not None

@pytest.mark.parametrize("path", [p for p in JSON_FILES if p.name == "package.json"], ids=_rel)
def test_package_json_has_name_and_version(path: Path) -> None:
    with path.open("r", encoding="utf-8") as f:
        pkg = json.load(f)
    assert isinstance(pkg.get("name"), str) and pkg["name"].strip(), "package.json must have non-empty 'name'."
    ver = pkg.get("version")
    assert isinstance(ver, str) and ver.strip(), "package.json must have non-empty 'version'."
    # Accept pre-releases/build metadata; require a semver-looking prefix.
    assert re.match(r"^\d+\.\d+\.\d+", ver) or ver == "0.0.0", f"version should start with MAJOR.MINOR.PATCH, got {ver!r}"

@pytest.mark.parametrize("path", TOML_FILES, ids=_rel)
def test_toml_files_are_valid(path: Path) -> None:
    data = load_toml_file(path)
    assert isinstance(data, dict)

@pytest.mark.parametrize("path", [p for p in TOML_FILES if p.name == "pyproject.toml"], ids=_rel)
def test_pyproject_has_expected_sections(path: Path) -> None:
    data = load_toml_file(path)
    assert "build-system" in data, "pyproject.toml must define [build-system]."
    has_project = "project" in data
    tool = data.get("tool") or {}
    has_tool_project = isinstance(tool, dict) and any(k in tool for k in ("poetry", "pdm", "hatch", "setuptools", "flit"))
    assert has_project or has_tool_project, (
        "pyproject.toml should have [project] or one of [tool.poetry|pdm|hatch|setuptools|flit]."
    )

@pytest.mark.parametrize("path", YAML_FILES, ids=_rel)
def test_yaml_files_are_valid(path: Path) -> None:
    yaml = pytest.importorskip("yaml", reason="PyYAML not installed")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data is not None

@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=_rel)
def test_github_action_workflows_have_jobs(path: Path) -> None:
    yaml = pytest.importorskip("yaml", reason="PyYAML not installed")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    assert isinstance(data, dict), "Workflow must be a mapping."
    assert "jobs" in data and isinstance(data["jobs"], dict), "Workflow should define jobs."
    assert "on" in data, "Workflow should define triggers under 'on'."

@pytest.mark.parametrize("path", INI_FILES, ids=_rel)
def test_ini_like_files_are_valid(path: Path) -> None:
    parser = configparser.ConfigParser(interpolation=None)
    with path.open("r", encoding="utf-8") as f:
        parser.read_file(f)
    # Require at least one explicit section (DEFAULT doesn't count)
    assert parser.sections(), f"{_rel(path)} should contain at least one section."

@pytest.mark.parametrize("path", [p for p in INI_FILES if p.name == "setup.cfg"], ids=_rel)
def test_setup_cfg_has_key_sections(path: Path) -> None:
    parser = configparser.ConfigParser(interpolation=None)
    with path.open("r", encoding="utf-8") as f:
        parser.read_file(f)
    assert any(s in parser for s in ("metadata", "options")), "setup.cfg should have [metadata] or [options]."

ENV_LINE_RE = re.compile(r"^(export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=\s*.*$")

@pytest.mark.parametrize("path", ENV_FILES, ids=_rel)
def test_env_files_have_valid_lines(path: Path) -> None:
    bad: list[tuple[int, str]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # allow empty values (KEY=) and quoted values; just enforce KEY=VALUE structure
            if not ENV_LINE_RE.match(line):
                bad.append((i, line))
    assert not bad, f"Invalid lines in {path}:\n" + "\n".join(f"{n}: {txt}" for n, txt in bad)

@pytest.mark.parametrize("path", COMPOSE_FILES, ids=_rel)
def test_docker_compose_has_services_section(path: Path) -> None:
    yaml = pytest.importorskip("yaml", reason="PyYAML not installed")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    assert "services" in data and isinstance(data["services"], dict), "docker compose file must define services."