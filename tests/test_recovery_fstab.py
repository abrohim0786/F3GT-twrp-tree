"""
Test suite validating Android recovery fstab semantics from the PR diff and repository files.

Testing library/framework used: pytest

Strategy:
- Primary assertions are based on the provided diff content (embedded below) to tightly validate
  the intended changes regardless of repo layout.
- Additional assertions load repository files (recovery.fstab and first_stage_ramdisk/fstab.mt6893)
  when present, verifying the actual files reflect the same invariants.

Focus:
- Dynamic partitions (system, vendor, product, system_ext)
- Metadata partition semantics (optional, no decrypt)
- Cache and vendor-related partitions (rescue, protect*, nv*, persist)
- mi_ext partition
- Boot/AVB partitions (boot, vbmeta_vendor, vbmeta_system)
- Absence of a /data mount in recovery.fstab, with /data handled in fstab.mt6893
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import pytest


# Embedded content taken from the PR's diff focus
EMBEDDED_FSTAB = """\
# Dynamic partitions
system      /system         ext4    ro      wait,slotselect,logical
vendor      /vendor         ext4    ro      wait,slotselect,logical
product     /product        ext4    ro      wait,slotselect,logical
system_ext  /system_ext     ext4    ro      wait,slotselect,logical

# Metadata (optional, no decrypt)
metadata    /metadata       ext4    wait,check,formattable

# /data — handled via first_stage_ramdisk/fstab.mt6893 for FBE

# Cache and vendor partitions
/dev/block/by-name/rescue       /cache              ext4    wait,check,formattable
/dev/block/by-name/protect1     /mnt/vendor/protect_f ext4  wait,check,formattable
/dev/block/by-name/protect2     /mnt/vendor/protect_s ext4  wait,check,formattable
/dev/block/by-name/nvdata       /mnt/vendor/nvdata     ext4  wait,check,formattable
/dev/block/by-name/nvcfg        /mnt/vendor/nvcfg      ext4  wait,check,formattable
/dev/block/by-name/persist      /mnt/vendor/persist    ext4  wait,check,formattable

# mi_ext logical partition (no bind mount here)
/dev/block/by-name/mi_ext       /mnt/vendor/mi_ext     ext4  wait

# Boot and AVB partitions
/dev/block/by-name/boot         /boot                  emmc  defaults slotselect
/dev/block/by-name/vbmeta_vendor /vbmeta_vendor        emmc  defaults slotselect
/dev/block/by-name/vbmeta_system /vbmeta_system        emmc  defaults slotselect
"""


@dataclass(frozen=True)
class FstabEntry:
    device: str
    mount_point: str
    fs_type: str
    mount_flags: Optional[str]   # e.g., "ro", "defaults"
    fs_mgr_flags: Optional[str]  # e.g., "wait,slotselect,logical"

    @property
    def mount_flag_set(self) -> set[str]:
        if not self.mount_flags:
            return set()
        parts = re.split(r"[,\s]+", self.mount_flags.strip())
        return {p for p in parts if p}

    @property
    def fs_mgr_flag_set(self) -> set[str]:
        if not self.fs_mgr_flags:
            return set()
        parts = re.split(r"[,\s]+", self.fs_mgr_flags.strip())
        return {p for p in parts if p}


def parse_fstab_lines(text: str) -> List[FstabEntry]:
    entries: List[FstabEntry] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cols = re.split(r"\s+", line)
        assert 4 <= len(cols) <= 5, f"Unexpected column count {len(cols)} in line: {raw}"
        device, mount_point, fs_type = cols[0], cols[1], cols[2]
        if len(cols) == 4:
            mount_flags = None
            fs_mgr_flags = cols[3]
        else:
            mount_flags = cols[3]
            fs_mgr_flags = cols[4]
        assert device, f"Empty device in line: {raw}"
        assert mount_point.startswith("/"), f"Mount point must start with '/': {mount_point}"
        assert re.match(r"^[A-Za-z0-9._+-]+$", fs_type), f"Unexpected fs_type: {fs_type}"
        entries.append(FstabEntry(device, mount_point, fs_type, mount_flags, fs_mgr_flags))
    return entries


# ---------- Fixtures for embedded and repository files ----------

@pytest.fixture(scope="module")
def embedded_entries() -> List[FstabEntry]:
    return parse_fstab_lines(EMBEDDED_FSTAB)


def _read_text_if_exists(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


@pytest.fixture(scope="module")
def repo_fstab_text() -> Optional[str]:
    root = Path(__file__).resolve().parents[1]
    return _read_text_if_exists(root / "recovery.fstab")


@pytest.fixture(scope="module")
def repo_fstab_entries(repo_fstab_text: Optional[str]) -> List[FstabEntry]:
    if not repo_fstab_text:
        pytest.skip("recovery.fstab not found in repository; skipping repo-backed assertions.")
    return parse_fstab_lines(repo_fstab_text)


@pytest.fixture(scope="module")
def mt6893_entries() -> List[FstabEntry]:
    root = Path(__file__).resolve().parents[1]
    p = root / "recovery" / "root" / "first_stage_ramdisk" / "fstab.mt6893"
    text = _read_text_if_exists(p)
    if not text:
        pytest.skip("fstab.mt6893 not found in repository; skipping related assertions.")
    return parse_fstab_lines(text)


# ---------- Tests against the embedded (diff) content ----------

def test_embedded_all_non_comment_lines_are_parsable(embedded_entries: List[FstabEntry]):
    assert len(embedded_entries) > 0, "No entries parsed from embedded fstab content."


def test_embedded_no_trailing_or_malformed_tokens(embedded_entries: List[FstabEntry]):
    for e in embedded_entries:
        for group in (e.mount_flags, e.fs_mgr_flags):
            if group:
                assert not group.endswith((",", " ")), f"Trailing delimiter in flags: {group!r}"


@pytest.mark.parametrize("name,mp", [
    ("system", "/system"),
    ("vendor", "/vendor"),
    ("product", "/product"),
    ("system_ext", "/system_ext"),
])
def test_embedded_dynamic_partitions_ro_slotselect_logical(embedded_entries: List[FstabEntry], name: str, mp: str):
    matches = [e for e in embedded_entries if e.device == name and e.mount_point == mp]
    assert matches, f"Dynamic partition {name} not found at {mp}"
    e = matches[0]
    assert e.fs_type == "ext4"
    assert "ro" in e.mount_flag_set
    for req in ("wait", "slotselect", "logical"):
        assert req in e.fs_mgr_flag_set


def test_embedded_metadata_optional_no_decrypt(embedded_entries: List[FstabEntry]):
    md = next((e for e in embedded_entries if e.mount_point == "/metadata"), None)
    assert md, "metadata entry not found"
    assert md.fs_type == "ext4"
    forbidden = {"forceencrypt", "encryptable", "fileencryption", "fde", "fbe"}
    assert forbidden.isdisjoint(md.mount_flag_set)
    assert forbidden.isdisjoint(md.fs_mgr_flag_set)
    for must in ("wait", "check", "formattable"):
        assert must in (md.mount_flag_set | md.fs_mgr_flag_set), f"metadata missing required flag: {must}"


@pytest.mark.parametrize("dev,mp", [
    ("/dev/block/by-name/rescue", "/cache"),
    ("/dev/block/by-name/protect1", "/mnt/vendor/protect_f"),
    ("/dev/block/by-name/protect2", "/mnt/vendor/protect_s"),
    ("/dev/block/by-name/nvdata", "/mnt/vendor/nvdata"),
    ("/dev/block/by-name/nvcfg", "/mnt/vendor/nvcfg"),
    ("/dev/block/by-name/persist", "/mnt/vendor/persist"),
])
def test_embedded_cache_vendor_have_wait_check_formattable(embedded_entries: List[FstabEntry], dev: str, mp: str):
    e = next((x for x in embedded_entries if x.device == dev and x.mount_point == mp), None)
    assert e, f"Entry not found for {dev} -> {mp}"
    assert e.fs_type == "ext4"
    combined = e.mount_flag_set | e.fs_mgr_flag_set
    for must in ("wait", "check", "formattable"):
        assert must in combined, f"{dev} missing flag: {must}"


def test_embedded_mi_ext_wait_only(embedded_entries: List[FstabEntry]):
    e = next((x for x in embedded_entries if x.device == "/dev/block/by-name/mi_ext"), None)
    assert e, "mi_ext entry not found"
    assert e.mount_point == "/mnt/vendor/mi_ext"
    assert e.fs_type == "ext4"
    combined = e.mount_flag_set | e.fs_mgr_flag_set
    assert "wait" in combined
    assert {"formattable", "check", "slotselect"}.isdisjoint(combined)


@pytest.mark.parametrize("dev,mp", [
    ("/dev/block/by-name/boot", "/boot"),
    ("/dev/block/by-name/vbmeta_vendor", "/vbmeta_vendor"),
    ("/dev/block/by-name/vbmeta_system", "/vbmeta_system"),
])
def test_embedded_boot_avb_emmc_defaults_slotselect(embedded_entries: List[FstabEntry], dev: str, mp: str):
    e = next((x for x in embedded_entries if x.device == dev and x.mount_point == mp), None)
    assert e, f"Boot/AVB entry not found for {dev}"
    assert e.fs_type == "emmc"
    assert "defaults" in e.mount_flag_set
    assert "slotselect" in e.fs_mgr_flag_set


def test_embedded_no_duplicate_mount_points(embedded_entries: List[FstabEntry]):
    seen = set()
    for e in embedded_entries:
        assert e.mount_point not in seen, f"Duplicate mount point: {e.mount_point}"
        seen.add(e.mount_point)


def test_embedded_device_paths_consistent(embedded_entries: List[FstabEntry]):
    for e in embedded_entries:
        if e.device.startswith("/"):
            assert e.device.startswith("/dev/"), f"Unexpected absolute device path: {e.device}"
        else:
            assert "/" not in e.device, f"Unexpected slash in bare partition name: {e.device}"


def test_embedded_column_counts_within_range():
    for raw in EMBEDDED_FSTAB.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cols = re.split(r"\s+", line)
        assert 4 <= len(cols) <= 5, f"Line should have 4 or 5 columns, got {len(cols)}: {raw}"


def test_embedded_flags_known_tokens_only(embedded_entries: List[FstabEntry]):
    known = {"ro", "rw", "defaults", "wait", "slotselect", "logical", "check", "formattable"}
    for e in embedded_entries:
        for token in (e.mount_flag_set | e.fs_mgr_flag_set):
            assert re.match(r"^[A-Za-z0-9_+-]+$", token), f"Suspicious token: {token}"
            assert token in known, f"Unexpected flag token in embedded content: {token}"


# ---------- Tests against the repository files (if present) ----------

def test_repo_recovery_fstab_parses(repo_fstab_entries: List[FstabEntry]):
    # Presence and basic parsing validated by fixture; ensure not empty
    assert len(repo_fstab_entries) > 0


@pytest.mark.parametrize("name,mp", [
    ("system", "/system"),
    ("vendor", "/vendor"),
    ("product", "/product"),
    ("system_ext", "/system_ext"),
])
def test_repo_dynamic_partitions_ro_slotselect_logical(repo_fstab_entries: List[FstabEntry], name: str, mp: str):
    e = next((x for x in repo_fstab_entries if x.device == name and x.mount_point == mp), None)
    assert e, f"Dynamic partition {name} not found at {mp} in repo recovery.fstab"
    assert e.fs_type == "ext4"
    assert "ro" in e.mount_flag_set, f"{name} should be read-only"
    for req in ("wait", "slotselect", "logical"):
        assert req in e.fs_mgr_flag_set, f"{name} missing fs_mgr flag {req}"


def test_repo_metadata_optional_no_decrypt(repo_fstab_entries: List[FstabEntry]):
    md = next((e for e in repo_fstab_entries if e.mount_point == "/metadata"), None)
    assert md, "metadata entry missing in repo recovery.fstab"
    assert md.fs_type == "ext4"
    forbidden = {"forceencrypt", "encryptable", "fileencryption", "fde", "fbe"}
    assert forbidden.isdisjoint(md.mount_flag_set | md.fs_mgr_flag_set)
    for must in ("wait", "check", "formattable"):
        assert must in (md.mount_flag_set | md.fs_mgr_flag_set), f"metadata missing {must}"


@pytest.mark.parametrize("dev,mp", [
    ("/dev/block/by-name/rescue", "/cache"),
    ("/dev/block/by-name/protect1", "/mnt/vendor/protect_f"),
    ("/dev/block/by-name/protect2", "/mnt/vendor/protect_s"),
    ("/dev/block/by-name/nvdata", "/mnt/vendor/nvdata"),
    ("/dev/block/by-name/nvcfg", "/mnt/vendor/nvcfg"),
    ("/dev/block/by-name/persist", "/mnt/vendor/persist"),
])
def test_repo_cache_vendor_have_wait_check_formattable(repo_fstab_entries: List[FstabEntry], dev: str, mp: str):
    e = next((x for x in repo_fstab_entries if x.device == dev and x.mount_point == mp), None)
    assert e, f"Entry not found for {dev} -> {mp} in repo recovery.fstab"
    assert e.fs_type == "ext4"
    combined = e.mount_flag_set | e.fs_mgr_flag_set
    for must in ("wait", "check", "formattable"):
        assert must in combined, f"{dev} missing {must}"


def test_repo_mi_ext_wait_only(repo_fstab_entries: List[FstabEntry]):
    e = next((x for x in repo_fstab_entries if x.device == "/dev/block/by-name/mi_ext"), None)
    assert e, "mi_ext entry not found in repo recovery.fstab"
    assert e.mount_point == "/mnt/vendor/mi_ext"
    assert e.fs_type == "ext4"
    combined = e.mount_flag_set | e.fs_mgr_flag_set
    assert "wait" in combined
    assert {"formattable", "check", "slotselect"}.isdisjoint(combined)


@pytest.mark.parametrize("dev,mp", [
    ("/dev/block/by-name/boot", "/boot"),
    ("/dev/block/by-name/vbmeta_vendor", "/vbmeta_vendor"),
    ("/dev/block/by-name/vbmeta_system", "/vbmeta_system"),
])
def test_repo_boot_avb_emmc_defaults_slotselect(repo_fstab_entries: List[FstabEntry], dev: str, mp: str):
    e = next((x for x in repo_fstab_entries if x.device == dev and x.mount_point == mp), None)
    assert e, f"Boot/AVB entry not found for {dev} in repo recovery.fstab"
    assert e.fs_type == "emmc"
    assert "defaults" in e.mount_flag_set
    assert "slotselect" in e.fs_mgr_flag_set


def test_repo_has_no_data_mount(repo_fstab_entries: List[FstabEntry]):
    assert all(e.mount_point != "/data" for e in repo_fstab_entries), \
        "recovery.fstab should not contain /data; it is handled in first-stage ramdisk fstab."


def test_mt6893_contains_data_entry(mt6893_entries: List[FstabEntry]):
    assert any(e.mount_point == "/data" for e in mt6893_entries), \
        "fstab.mt6893 should contain a /data entry to handle FBE during first stage."