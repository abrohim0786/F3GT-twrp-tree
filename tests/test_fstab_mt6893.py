# Testing library/framework: pytest
# These tests validate the Android fstab for MT6893. They focus on ensuring
# mount entries, flags, and fs_mgr options are present and correct, covering
# happy paths and critical edge cases seen in the PR diff.

from __future__ import annotations

from pathlib import Path
import fnmatch
import pytest


def locate_fstab_mt6893() -> Path:
    """
    Find the MT6893 fstab file in the repository.
    We search for 'fstab.in.mt6893' so tests work regardless of exact vendor path.
    """
    candidates = [p for p in Path(".").rglob("fstab.in.mt6893") if p.is_file()]
    if not candidates:
        pytest.skip("MT6893 fstab not found (fstab.in.mt6893). Skipping MT6893-specific tests.")
    # Prefer the one that lives under an 'mt6893' directory, then shortest path
    candidates = sorted(
        candidates,
        key=lambda p: (0 if "mt6893" in str(p.parent) else 1, len(str(p)))
    )
    return candidates[0]


def parse_android_fstab(text: str):
    """
    Parse AOSP/Android-style fstab lines into a structured representation.
    Format per line (whitespace-separated):
      0: spec (device/label/pattern)
      1: mount_point
      2: fstype
      3: mount_flags (comma-separated; may include key=value like lowerdir=...)
      4: fs_mgr_flags (comma-separated; may include key=value like avb=..., fileencryption=...)
    Lines starting with '#' or blank lines are skipped.
    """
    entries = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            # Not a valid fstab row for our purposes; skip defensively
            continue
        spec, mount_point, fstype = parts[0], parts[1], parts[2]
        mount_flags = parts[3] if len(parts) >= 4 else ""
        fs_mgr_flags = parts[4] if len(parts) >= 5 else ""

        def split_flags(flags_blob: str):
            flag_set = set()
            flag_kv = {}
            if not flags_blob:
                return flag_set, flag_kv
            for token in [t for t in flags_blob.split(",") if t]:
                if "=" in token:
                    k, v = token.split("=", 1)
                    flag_kv[k] = v
                else:
                    flag_set.add(token)
            return flag_set, flag_kv

        mflag_set, mflag_kv = split_flags(mount_flags)
        fsmgr_set, fsmgr_kv = split_flags(fs_mgr_flags)

        entries.append({
            "spec": spec,
            "mount_point": mount_point,
            "fstype": fstype,
            "mount_flags": mflag_set,
            "mount_opts": mflag_kv,        # e.g., lowerdir=...
            "fs_mgr_flags": fsmgr_set,
            "fs_mgr_opts": fsmgr_kv,       # e.g., avb=..., fileencryption=...
            "raw": raw,
        })
    return entries


@pytest.fixture(scope="module")
def fstab_text() -> str:
    path = locate_fstab_mt6893()
    return path.read_text(encoding="utf-8", errors="ignore")


@pytest.fixture(scope="module")
def entries(fstab_text: str):
    return parse_android_fstab(fstab_text)


def _by_mount(entries, mount_point: str):
    return [e for e in entries if e["mount_point"] == mount_point]


def _by_spec_glob(entries, pattern: str):
    return [e for e in entries if fnmatch.fnmatch(e["spec"], pattern)]


def test_fstab_mt6893_file_is_present_and_parses(entries):
    # Happy path: we found and parsed at least one valid entry
    assert isinstance(entries, list) and len(entries) > 0, "No fstab entries were parsed."


@pytest.mark.parametrize("mp", ["/system", "/vendor", "/product", "/system_ext"])
def test_readonly_ab_partitions_have_ext4_and_erofs_variants(entries, mp):
    es = _by_mount(entries, mp)
    # Expect exactly two entries: one for ext4, one for erofs
    ftypes = {e["fstype"] for e in es}
    assert ftypes == {"ext4", "erofs"}, f"{mp} should have ext4 and erofs entries; got {ftypes}"
    # Read-only mount flag must be present and no 'rw' in mount flags
    for e in es:
        assert "ro" in e["mount_flags"], f"{mp} ({e['fstype']}) must be mounted read-only"
        assert "rw" not in e["mount_flags"], f"{mp} ({e['fstype']}) must not be mounted read-write"
        # A/B (slotselect) + logical + first_stage_mount are required
        for req in ("slotselect", "logical", "first_stage_mount"):
            assert req in (e["fs_mgr_flags"] | set(e["fs_mgr_opts"].keys())), f"{mp} missing {req}"


def test_system_has_avb_and_avb_keys(entries):
    # System must bind to vbmeta_system and include AVB pubkeys (q/r/s)
    es = _by_mount(entries, "/system")
    assert len(es) == 2, "Expected ext4 and erofs entries for /system"
    for e in es:
        # avb=vbmeta_system
        assert e["fs_mgr_opts"].get("avb") == "vbmeta_system", "system must specify avb=vbmeta_system"
        # avb_keys should include q/r/s GSI keys
        keys = e["fs_mgr_opts"].get("avb_keys")
        assert keys, "system must provide avb_keys"
        parts = [p.split("/")[-1] for p in keys.split(":")]
        for expected in ("q-gsi.avbpubkey", "r-gsi.avbpubkey", "s-gsi.avbpubkey"):
            assert expected in parts, f"system avb_keys missing {expected}"


@pytest.mark.parametrize("mp", ["/vendor", "/product", "/system_ext"])
def test_vendor_product_systemext_have_avb_and_boot_flags(entries, mp):
    es = _by_mount(entries, mp)
    for e in es:
        # avb flag (with or without value) must be present
        has_avb_flag = "avb" in e["fs_mgr_flags"] or "avb" in e["fs_mgr_opts"]
        assert has_avb_flag, f"{mp} must enable AVB"
        # Ensure boot-time flags
        for req in ("slotselect", "logical", "first_stage_mount"):
            assert req in (e["fs_mgr_flags"] | set(e["fs_mgr_opts"].keys())), f"{mp} missing {req}"


def test_mi_ext_and_bind_overlay(entries):
    # /mnt/vendor/mi_ext should appear as ext4 & erofs with avb=vbmeta and nofail
    es = _by_mount(entries, "/mnt/vendor/mi_ext")
    ftypes = {e["fstype"] for e in es}
    assert ftypes == {"ext4", "erofs"}, "mi_ext must have ext4 and erofs variants"
    for e in es:
        assert "ro" in e["mount_flags"]
        assert e["fs_mgr_opts"].get("avb") == "vbmeta", "mi_ext must specify avb=vbmeta"
        for req in ("logical", "first_stage_mount", "nofail"):
            assert req in (e["fs_mgr_flags"] | set(e["fs_mgr_opts"].keys()))
    # Bind mount to /mi_ext
    bind = _by_mount(entries, "/mi_ext")
    assert len(bind) == 1 and bind[0]["fstype"] == "none", "Expected bind mount to /mi_ext"
    assert "ro" in bind[0]["mount_flags"] and "bind" in bind[0]["mount_flags"]
    for req in ("wait", "nofail"):
        assert req in (bind[0]["fs_mgr_flags"] | set(bind[0]["fs_mgr_opts"].keys()))


def _normalize_dirs(v: str):
    return [p.rstrip("/") for p in v.split(":") if p]


def test_overlay_layers_and_order(entries):
    # Validate overlay mount lowerdir ordering and fs_mgr flags (check, nofail)
    expected = {
        "/product/overlay": ["/mnt/vendor/mi_ext/product/overlay", "/product/overlay"],
        "/product/app": ["/mnt/vendor/mi_ext/product/app", "/product/app"],
        "/product/priv-app": ["/mnt/vendor/mi_ext/product/priv-app", "/product/priv-app"],
        "/product/lib": ["/mnt/vendor/mi_ext/product/lib", "/product/lib"],
        "/product/lib64": ["/mnt/vendor/mi_ext/product/lib64", "/product/lib64"],
        "/product/bin": ["/mnt/vendor/mi_ext/product/bin", "/product/bin"],
        "/product/framework": ["/mnt/vendor/mi_ext/product/framework", "/product/framework"],
        "/product/media": ["/mnt/vendor/mi_ext/product/media", "/product/media"],
        "/product/opcust": ["/mnt/vendor/mi_ext/product/opcust", "/product/opcust"],
        "/product/data-app": ["/mnt/vendor/mi_ext/product/data-app", "/product/data-app"],
        "/product/etc/sysconfig": ["/mnt/vendor/mi_ext/product/etc/sysconfig", "/product/etc/sysconfig"],
        "/product/etc/permissions": ["/mnt/vendor/mi_ext/product/etc/permissions", "/product/etc/permissions"],
        "/system/app": ["/mnt/vendor/mi_ext/system/app", "/product/pangu/system/app", "/system/app"],
        "/system/priv-app": ["/mnt/vendor/mi_ext/system/priv-app", "/product/pangu/system/priv-app", "/system/priv-app"],
        "/system/framework": ["/product/pangu/system/framework", "/system/framework"],
        "/system/etc/sysconfig": ["/mnt/vendor/mi_ext/system/etc/sysconfig", "/system/etc/sysconfig"],
        "/system/etc/permissions": ["/mnt/vendor/mi_ext/system/etc/permissions", "/product/pangu/system/etc/permissions", "/system/etc/permissions"],
        "/system/lib": ["/product/pangu/system/lib", "/system/lib"],
        "/system/lib64": ["/product/pangu/system/lib64", "/system/lib64"],
    }
    overlays = {e["mount_point"]: e for e in entries if e["fstype"] == "overlay"}
    for mp, expected_chain in expected.items():
        assert mp in overlays, f"Missing overlay mount for {mp}"
        e = overlays[mp]
        # Must be read-only overlay
        assert "ro" in e["mount_flags"], f"{mp} overlay must be ro"
        # lowerdir must exist and be ordered as expected (normalizing trailing slashes)
        lower = e["mount_opts"].get("lowerdir")
        assert lower, f"{mp} overlay missing lowerdir"
        got_chain = _normalize_dirs(lower)
        assert got_chain == expected_chain, f"{mp} overlay lowerdir chain mismatch.\nExpected: {expected_chain}\nGot:      {got_chain}"
        # fs_mgr flags check & nofail
        for req in ("check", "nofail"):
            assert req in (e["fs_mgr_flags"] | set(e["fs_mgr_opts"].keys())), f"{mp} overlay missing {req}"


def test_metadata_partition_flags(entries):
    meta = [e for e in entries if e["spec"].endswith("/by-name/metadata") and e["mount_point"] == "/metadata"]
    assert meta, "metadata partition entry missing"
    e = meta[0]
    assert e["fstype"] == "ext4"
    for f in ("noatime", "nosuid", "nodev", "discard"):
        assert f in e["mount_flags"]
    for req in ("wait", "check", "formattable", "first_stage_mount"):
        assert req in (e["fs_mgr_flags"] | set(e["fs_mgr_opts"].keys()))


def test_userdata_partition_encryption_quota_and_integrity(entries):
    data = [e for e in entries if e["spec"].endswith("/by-name/userdata") and e["mount_point"] == "/data"]
    assert data, "userdata (/data) entry missing"
    e = data[0]
    assert e["fstype"] == "ext4"
    # Mount flags baseline
    for f in ("noatime", "nosuid", "nodev", "discard"):
        assert f in e["mount_flags"]
    # Specific mount flags
    for f in ("fsync_mode=nobarrier", "reserve_root=134217", "resgid=1065", "inlinecrypt"):
        # inlinecrypt can sometimes appear via fileencryption, but keep a friendly check here too
        assert (f in e["mount_flags"]) or (f.split("=")[0] in e["fs_mgr_opts"].get("fileencryption", "")), f"/data missing {f}"
    # fs_mgr flags and options
    req_fs_mgr_flags = {"wait", "check", "formattable", "quota", "latemount", "resize", "fsverity"}
    assert req_fs_mgr_flags.issubset(e["fs_mgr_flags"] | set(e["fs_mgr_opts"].keys())), f"/data missing one of {req_fs_mgr_flags}"
    assert e["fs_mgr_opts"].get("reservedsize") == "128m", "/data must have reservedsize=128m"
    assert e["fs_mgr_opts"].get("checkpoint") == "fs", "/data must have checkpoint=fs"
    # Encryption mode must include v2+inlinecrypt_optimized
    fe = e["fs_mgr_opts"].get("fileencryption", "")
    assert "v2+inlinecrypt_optimized" in fe, "/data fileencryption must include v2+inlinecrypt_optimized"
    assert e["fs_mgr_opts"].get("keydirectory") == "/metadata/vold/metadata_encryption", "/data keydirectory mismatch"


def test_voldmanaged_external_and_usbotg(entries):
    # SD card slot with encryptable userdata
    sd = _by_spec_glob(entries, "/devices/platform/externdevice*")
    assert sd, "Expected voldmanaged sdcard1 entry"
    sd_e = sd[0]
    assert sd_e["fstype"] == "auto"
    assert "defaults" in sd_e["mount_flags"]
    assert "voldmanaged" in sd_e["fs_mgr_opts"]
    assert sd_e["fs_mgr_opts"]["voldmanaged"].startswith("sdcard1:")
    assert sd_e["fs_mgr_opts"].get("encryptable") == "userdata"

    # USB OTG entries
    otg1 = _by_spec_glob(entries, "/devices/platform/usb_xhci*")
    otg2 = _by_spec_glob(entries, "/devices/platform/soc/11201000.usb0/11200000.xhci*")
    assert otg1 or otg2, "Expected at least one usbotg voldmanaged entry"
    for e in otg1 + otg2:
        assert e["fstype"] == "vfat"
        assert "defaults" in e["mount_flags"]
        assert e["fs_mgr_opts"].get("voldmanaged", "").startswith("usbotg:")


def test_boot_and_vbmeta_entries_have_required_flags(entries):
    # /boot must be first_stage_mount and slotselect
    boot = [e for e in entries if e["spec"].endswith("/by-name/boot") and e["mount_point"] == "/boot"]
    assert boot, "Missing /boot entry"
    for req in ("first_stage_mount", "slotselect", "nofail"):
        assert req in (boot[0]["fs_mgr_flags"] | set(boot[0]["fs_mgr_opts"].keys()))
    # vbmeta partitions
    vb_vendor = [e for e in entries if e["spec"].endswith("/by-name/vbmeta_vendor")]
    vb_system = [e for e in entries if e["spec"].endswith("/by-name/vbmeta_system")]
    assert vb_vendor, "Missing vbmeta_vendor"
    assert vb_system, "Missing vbmeta_system"
    for e in vb_vendor + vb_system:
        for req in ("first_stage_mount", "slotselect", "nofail"):
            assert req in (e["fs_mgr_flags"] | set(e["fs_mgr_opts"].keys()))
    # vbmeta_system must specify avb=vbmeta
    assert vb_system[0]["fs_mgr_opts"].get("avb") == "vbmeta", "vbmeta_system must include avb=vbmeta"


def test_no_rw_on_key_readonly_partitions(entries):
    # Ensure none of the key read-only partitions accidentally mount as rw
    for mp in ("/system", "/vendor", "/product", "/system_ext"):
        for e in _by_mount(entries, mp):
            assert "rw" not in e["mount_flags"], f"{mp} has unexpected rw flag"

