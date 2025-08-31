# ruff: noqa: S101, S603, TRY003
# Framework: pytest
# Purpose: Validate environment exports and detection logic in vendorsetup.sh for device "ares".
# Scenarios covered:
#  - Argument-based activation ($1 == "ares")
#  - FOX_BUILD_DEVICE environment variable activation
#  - Auto-detection via BASH_SOURCE path containing "ares"
#  - Fallback detection via BASH_ARGV when no args and path lacks "ares"
#  - Negative path: no activation when device mismatches
#  - Logging behavior with FOX_BUILD_LOG_FILE
import os
import re
import shutil
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope="module", autouse=True)
def ensure_bash_available():
    if shutil.which("bash") is None:
        pytest.skip("bash is required to run these tests")

def _capture_env_from_bytes(raw: bytes) -> dict:
    env_map = {}
    for chunk in raw.split(b"\x00"):
        if b"=" in chunk:
            k, v = chunk.split(b"=", 1)
            try:
                env_map[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
            except UnicodeDecodeError:
                env_map[k.decode("utf-8", "ignore")] = v.decode("utf-8", "ignore")
    return env_map

def _run_bash_capture_env(commands: str, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    bash = shutil.which("bash") or "bash"
    proc = subprocess.run(  # noqa: S603
        [bash, "-lc", f"{commands}; env -0"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=False,
    )
    return _capture_env_from_bytes(proc.stdout)

def _run_bash_with_extra_shell_args(commands: str, shell_args: list[str]):
    bash = shutil.which("bash") or "bash"
    # Pass extra arguments to `bash -lc` so they populate BASH_ARGV in that shell.
    proc = subprocess.run(  # noqa: S603
        [bash, "-lc", f"{commands}; env -0", *shell_args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    return _capture_env_from_bytes(proc.stdout)

def _discover_script_path(repo_root: Path) -> Path:
    # 1) Common/known path
    p = repo_root / "vendorsetup.sh"
    if p.exists():
        return p

    # 2) Search all *.sh for marker (no dependency on ripgrep)
    for sh in repo_root.rglob("*.sh"):
        try:
            txt = sh.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if 'FDEVICE="ares"' in txt or "fox_get_target_device()" in txt:
            return sh

    raise FileNotFoundError()

@pytest.fixture(scope="module")
def script_path() -> Path:
    return _discover_script_path(REPO_ROOT)

def _assert_core_exports(env_map: dict):
    assert env_map.get("TW_DEFAULT_LANGUAGE") == "en"
    assert env_map.get("LC_ALL") == "C"
    assert env_map.get("FOX_VIRTUAL_AB_DEVICE") == "1"
    assert env_map.get("ALLOW_MISSING_DEPENDENCIES") == "true"
    assert env_map.get("OF_SCREEN_H") == "2340"
    assert env_map.get("OF_CLOCK_POS") == "2"
    assert env_map.get("FOX_RECOVERY_BOOT_PARTITION") == "/dev/block/by-name/boot"
    zip_path = env_map.get("FOX_USE_SPECIFIC_MAGISK_ZIP")
    assert zip_path is not None and zip_path.endswith("/magisk/magisk.zip")
    assert "/ares/" in zip_path or zip_path.startswith("device/xiaomi/ares")
    assert env_map.get("FOX_R11") == "3"
    # YYYYMMDD format (per diff shows 20250824)
    patch_version = env_map.get("FOX_MAINTAINER_PATCH_VERSION")
    assert patch_version and re.fullmatch(r"\d{8}", patch_version)
    assert env_map.get("FOX_BUILD_TYPE") in {"Unofficial", "Official", "Beta"}
    assert env_map.get("FOX_VARIANT") is not None
    assert env_map.get("OF_PATCH_AVB20") == "1"
    assert env_map.get("OF_ADVANCED_SECURITY") == "1"
    assert env_map.get("OF_RUN_POST_FORMAT_PROCESS") == "1"

def _assert_not_exported(env_map: dict):
    # A reliable signal: this variable is only present when the script activates
    assert env_map.get("FOX_VIRTUAL_AB_DEVICE") is None

def test_exports_when_argument_matches(script_path: Path):
    env_map = _run_bash_capture_env(f"set -a; source '{script_path}' ares")
    _assert_core_exports(env_map)

def test_exports_when_env_FOX_BUILD_DEVICE_matches(script_path: Path):
    env_map = _run_bash_capture_env(
        f"set -a; source '{script_path}'", extra_env={"FOX_BUILD_DEVICE": "ares"}
    )
    _assert_core_exports(env_map)

def test_no_exports_when_argument_does_not_match(script_path: Path):
    env_map = _run_bash_capture_env(f"set -a; source '{script_path}' otherdevice")
    _assert_not_exported(env_map)

def test_auto_detection_via_BASH_SOURCE_path(script_path: Path, tmp_path: Path):
    # Create a symlink under a path containing 'ares' to trigger BASH_SOURCE grep
    ares_dir = tmp_path / "device" / "xiaomi" / "ares"
    ares_dir.mkdir(parents=True, exist_ok=True)
    linked = ares_dir / "vendorsetup_symlink.sh"
    try:
        if not linked.exists():
            linked.symlink_to(script_path.resolve())
    except OSError:
        shutil.copy2(script_path, linked)
    env_map = _run_bash_capture_env(f"set -a; source '{linked}'")
    _assert_core_exports(env_map)

def test_fallback_detection_via_BASH_ARGV(script_path: Path, tmp_path: Path):
    # Place a copy in a neutral path so BASH_SOURCE doesn't match
    neutral_dir = tmp_path / "neutral_path_without_keyword"
    neutral_dir.mkdir(parents=True, exist_ok=True)
    copy_path = neutral_dir / "vendorsetup_copy.sh"
    shutil.copy2(script_path, copy_path)
    # Do not pass arguments to 'source' (so $1 is empty).
    # Instead, pass "ares" as an extra arg to `bash -lc`, which should populate BASH_ARGV.
    env_map = _run_bash_with_extra_shell_args(f"set -a; source '{copy_path}'", ["ares"])
    _assert_core_exports(env_map)

def test_logging_to_FOX_BUILD_LOG_FILE(script_path: Path, tmp_path: Path):
    log_file = tmp_path / "fox_build.log"
    log_file.write_text("", encoding="utf-8")
    _ = _run_bash_capture_env(
        f"set -a; export FOX_BUILD_LOG_FILE='{log_file}'; source '{script_path}' ares"
    )
    content = log_file.read_text(encoding="utf-8", errors="replace")
    assert "FOX_R11" in content
    assert "FOX_MAINTAINER_PATCH_VERSION" in content
    assert "OF_" in content

def test_critical_flag_values_and_formats(script_path: Path):
    env_map = _run_bash_capture_env(f"set -a; source '{script_path}' ares")
    for key in [
        "OF_FLASHLIGHT_ENABLE",
        "OF_KEEP_DM_VERITY_FORCED_ENCRYPTION",
        "OF_FIX_OTA_UPDATE_MANUAL_FLASH_ERROR",
        "OF_NO_TREBLE_COMPATIBILITY_CHECK",
        "OF_DONT_PATCH_ENCRYPTED_DEVICE",
        "FOX_USE_TWRP_RECOVERY_IMAGE_BUILDER",
        "OF_SKIP_MULTIUSER_FOLDERS_BACKUP",
        "FOX_DELETE_AROMAFM",
        "OF_USE_GREEN_LED",
        "FOX_ENABLE_APP_MANAGER",
        "OF_SKIP_DECRYPTED_ADOPTED_STORAGE",
        "OF_PATCH_AVB20",
        "OF_ADVANCED_SECURITY",
        "OF_USE_TWRP_SAR_DETECT",
        "OF_RUN_POST_FORMAT_PROCESS",
    ]:
        assert env_map.get(key) == "1", f"{key} should be '1'"

    # Verify quick backup list format
    qbl = env_map.get("OF_QUICK_BACKUP_LIST")
    assert qbl is not None and all(p.startswith("/") for p in qbl.split(";") if p)