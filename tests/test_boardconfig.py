"""
Tests for BoardConfig configuration values.

Testing library/framework:
- Preferred: pytest (if installed/executed by the project CI).
- The tests are written to be compatible with both pytest and unittest discovery.
  They use plain asserts (pytest style) which also work under unittest when executed by pytest.

Scope:
- Validate the Android BoardConfig settings for device/xiaomi/ares as per the PR diff.
- Since this is a Make-style config file (BoardConfig.mk or similar), tests parse lines to a simple mapping
  and also support '+=' accumulation for multi-valued variables.

Behavior:
- These tests DO NOT attempt to evaluate Make variable indirection. They check raw string values.
- If the BoardConfig file cannot be found, tests will fail with a helpful error.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Candidate locations for the board config file. We search these (most common path first).
CANDIDATE_FILES = [
    Path("device/xiaomi/ares/BoardConfig.mk"),
    Path("BoardConfig.mk"),
    # Fallback: any found in repo under device/xiaomi/ares (CI may relocate)
]

def find_board_config() -> Path:
    # Direct hits
    for p in CANDIDATE_FILES:
        if p.exists():
            return p

    # Fallback: scan repo for a BoardConfig.mk that contains our distinctive values
    repo_root = Path(".")
    candidates = list(repo_root.rglob("BoardConfig.mk"))
    distinctive = [
        "DEVICE_PATH := device/xiaomi/ares",
        "TARGET_OTA_ASSERT_DEVICE := ares,aresin",
        "PLATFORM_VERSION := 99.87.36",
        "PLATFORM_SECURITY_PATCH := 2099-12-31",
        "TW_INCLUDE_CRYPTO := true",
    ]
    for c in candidates:
        try:
            text = c.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if all(s in text for s in distinctive):
            return c

    raise FileNotFoundError(
        "Unable to locate BoardConfig.mk with expected ares settings. "
        "Checked common paths and scanned repository."
    )

def parse_boardconfig_lines(lines: List[str]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Parse a subset of Makefile-like variable assignments.

    Supported:
      NAME := VALUE
      NAME += VALUE
    Returns:
      - values: last ':=' scalar values
      - accum: dict of list accumulations for '+=' (we also include ':=' as first element for convenience)
    """
    assign_re = re.compile(r'^\s*([A-Za-z0-9_]+)\s*(:=|\+=)\s*(.*\S)\s*$')
    values: Dict[str, str] = {}
    accum: Dict[str, List[str]] = {}
    for raw in lines:
        m = assign_re.match(raw)
        if not m:
            continue
        name, op, val = m.groups()
        if op == ":=":
            values[name] = val
            # initialize accumulation list with the base value so that tests can search in combined content
            accum.setdefault(name, [])
            # Only store base once; if := appears again we reset both places to reflect overriding semantics
            accum[name] = [val]
        else:  # +=
            values.setdefault(name, "")
            accum.setdefault(name, [])
            accum[name].append(val)
    return values, accum

def load_parsed() -> Tuple[Path, Dict[str, str], Dict[str, List[str]]]:
    cfg = find_board_config()
    text = cfg.read_text(encoding="utf-8", errors="ignore").splitlines()
    values, accum = parse_boardconfig_lines(text)
    return cfg, values, accum

def combined_value(accum: Dict[str, List[str]], key: str) -> str:
    """Join accumulations with spaces to emulate typical Make behavior for our assertions."""
    parts = accum.get(key, [])
    return " ".join(parts).strip()

def test_boardconfig_file_present():
    cfg = find_board_config()
    assert cfg.exists(), "BoardConfig.mk must exist"

def test_device_path_and_platform_version_hack():
    _, values, _ = load_parsed()
    assert values.get("DEVICE_PATH") == "device/xiaomi/ares"
    assert values.get("PLATFORM_VERSION") == "99.87.36"
    assert values.get("PLATFORM_SECURITY_PATCH") == "2099-12-31"
    # VENDOR_SECURITY_PATCH mirrors PLATFORM_SECURITY_PATCH via variable reference
    assert values.get("VENDOR_SECURITY_PATCH") == "$(PLATFORM_SECURITY_PATCH)"
    assert values.get("PLATFORM_VERSION_LAST_STABLE") == "$(PLATFORM_VERSION)"

def test_architecture_settings():
    _, values, _ = load_parsed()
    assert values.get("TARGET_ARCH") == "arm64"
    assert values.get("TARGET_ARCH_VARIANT") == "armv8-a"
    assert values.get("TARGET_CPU_ABI") == "arm64-v8a"
    assert values.get("TARGET_CPU_VARIANT") == "cortex-a55"

    # Second arch
    assert values.get("TARGET_2ND_ARCH") == "arm"
    assert values.get("TARGET_2ND_ARCH_VARIANT") == "armv8-2a"
    assert values.get("TARGET_2ND_CPU_ABI") == "armeabi-v7a"
    assert values.get("TARGET_2ND_CPU_ABI2") == "armeabi"
    assert values.get("TARGET_2ND_CPU_VARIANT") == "cortex-a55"

def test_bootloader_and_platform():
    _, values, _ = load_parsed()
    assert values.get("TARGET_BOOTLOADER_BOARD_NAME") == "ares"
    assert values.get("TARGET_NO_BOOTLOADER") == "true"
    assert values.get("TARGET_USES_UEFI") == "true"
    assert values.get("TARGET_BOARD_PLATFORM") == "mt6893"

def test_ota_assert_device():
    _, values, _ = load_parsed()
    assert values.get("TARGET_OTA_ASSERT_DEVICE") == "ares,aresin"

def test_kernel_prebuilts_and_cmdline():
    _, values, accum = load_parsed()
    assert values.get("TARGET_PREBUILT_KERNEL") == "$(DEVICE_PATH)/prebuilt/kernel"
    assert values.get("TARGET_PREBUILT_DTB") == "$(DEVICE_PATH)/prebuilt/dtb.img"
    # Command line is provided via ':=' first then '+=' lines; validate combined contains both tokens
    combined = combined_value(accum, "BOARD_KERNEL_CMDLINE")
    assert "bootopt=64S3,32N2,64N2" in combined
    assert "androidboot.force_normal_boot=1" in combined

    assert values.get("BOARD_BOOTIMG_HEADER_VERSION") == "2"
    assert values.get("BOARD_KERNEL_BASE") == "0x40078000"
    assert values.get("BOARD_KERNEL_PAGESIZE") == "2048"
    assert values.get("BOARD_RAMDISK_OFFSET") == "0x11088000"
    assert values.get("BOARD_KERNEL_TAGS_OFFSET") == "0x07c08000"
    assert values.get("BOARD_DTB_OFFSET") == "0x07c08000"
    assert values.get("BOARD_KERNEL_IMAGE_NAME") == "kernel"

def test_mkbootimg_args_include_required_flags():
    _, _, accum = load_parsed()
    mkargs = combined_value(accum, "BOARD_MKBOOTIMG_ARGS")
    # Ensure mkbootimg args include key parameters
    assert "--dtb $(TARGET_PREBUILT_DTB)" in mkargs
    assert "--ramdisk_offset $(BOARD_RAMDISK_OFFSET)" in mkargs
    assert "--tags_offset $(BOARD_KERNEL_TAGS_OFFSET)" in mkargs
    assert "--header_version $(BOARD_BOOTIMG_HEADER_VERSION)" in mkargs

def test_avb_settings():
    _, values, _ = load_parsed()
    assert values.get("BOARD_AVB_ENABLE") == "true"
    # vbmeta flags
    assert values.get("BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS") == "--flags 3"

    # Recovery AVB
    assert values.get("BOARD_AVB_RECOVERY_KEY_PATH") == "external/avb/test/data/testkey_rsa4096.pem"
    assert values.get("BOARD_AVB_RECOVERY_ALGORITHM") == "SHA256_RSA4096"
    assert values.get("BOARD_AVB_RECOVERY_ROLLBACK_INDEX") == "1"
    assert values.get("BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION") == "1"

    # VBMETA system chain
    assert values.get("BOARD_AVB_VBMETA_SYSTEM") == "system system_ext product"
    assert values.get("BOARD_AVB_VBMETA_SYSTEM_KEY_PATH") == "external/avb/test/data/testkey_rsa2048.pem"
    assert values.get("BOARD_AVB_VBMETA_SYSTEM_ALGORITHM") == "SHA256_RSA2048"
    assert values.get("BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX") == "$(PLATFORM_SECURITY_PATCH_TIMESTAMP)"
    assert values.get("BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION") == "2"

    # VBMETA vendor chain
    assert values.get("BOARD_AVB_VBMETA_VENDOR") == "vendor"
    assert values.get("BOARD_AVB_VBMETA_VENDOR_KEY_PATH") == "external/avb/test/data/testkey_rsa2048.pem"
    assert values.get("BOARD_AVB_VBMETA_VENDOR_ALGORITHM") == "SHA256_RSA2048"
    assert values.get("BOARD_AVB_VBMETA_VENDOR_ROLLBACK_INDEX") == "$(PLATFORM_SECURITY_PATCH_TIMESTAMP)"
    assert values.get("BOARD_AVB_VBMETA_VENDOR_ROLLBACK_INDEX_LOCATION") == "1"

def test_encryption_fbe_and_metadata():
    _, values, _ = load_parsed()
    assert values.get("TW_INCLUDE_CRYPTO") == "true"
    assert values.get("TW_INCLUDE_FBE") == "true"
    assert values.get("BOARD_USES_METADATA_PARTITION") == "true"
    assert values.get("TW_INCLUDE_FBE_METADATA_DECRYPT") == "true"
    assert values.get("TW_USE_FSCRYPT_POLICY") == "v2"

def test_fstab_and_wipe_paths():
    _, values, _ = load_parsed()
    assert values.get("TARGET_RECOVERY_FSTAB") == "$(DEVICE_PATH)/recovery.fstab"
    assert values.get("TARGET_RECOVERY_WIPE") == "$(DEVICE_PATH)/recovery.wipe"

def test_partition_sizes_and_types():
    _, values, _ = load_parsed()
    # Sizes should be numeric strings; parse to int to validate syntax
    assert int(values.get("BOARD_BOOTIMAGE_PARTITION_SIZE")) == 134217728
    assert int(values.get("BOARD_USERDATAIMAGE_PARTITION_SIZE")) == 115234275328
    assert int(values.get("BOARD_DTBOIMG_PARTITION_SIZE")) == 33554432

    # Filesystem types
    assert values.get("BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE") == "ext4"
    assert values.get("BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE") == "ext4"
    assert values.get("BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE") == "ext4"
    assert values.get("BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE") == "ext4"

    # Super partitions
    assert values.get("BOARD_SUPER_PARTITION_GROUPS") == "main"
    assert int(values.get("BOARD_SUPER_PARTITION_SIZE")) == 9126805504
    assert values.get("BOARD_MAIN_PARTITION_LIST") == "product system system_ext vendor"
    assert int(values.get("BOARD_MAIN_SIZE")) == 9122611200

def test_target_copy_out_mappings():
    _, values, _ = load_parsed()
    assert values.get("TARGET_COPY_OUT_PRODUCT") == "product"
    assert values.get("TARGET_COPY_OUT_SYSTEM_EXT") == "system_ext"
    assert values.get("TARGET_COPY_OUT_VENDOR") == "vendor"

def test_recovery_and_build_flags():
    _, values, _ = load_parsed()
    assert values.get("BOARD_HAS_LARGE_FILESYSTEM") == "true"
    assert values.get("BOARD_HAS_NO_SELECT_BUTTON") == "true"
    assert values.get("BOARD_SUPPRESS_SECURE_ERASE") == "true"
    assert values.get("TARGET_RECOVERY_PIXEL_FORMAT") == '"RGBX_8888"'
    assert values.get("BOARD_USES_RECOVERY_AS_BOOT") == "true"
    assert values.get("TARGET_NO_RECOVERY") == "true"

def test_root_and_system_as_root_flags():
    _, values, _ = load_parsed()
    assert values.get("BOARD_ROOT_EXTRA_FOLDERS") == "cust"
    assert values.get("BOARD_BUILD_SYSTEM_ROOT_IMAGE") == "false"

def test_treble_and_super_meta():
    _, values, _ = load_parsed()
    assert values.get("BOARD_VNDK_VERSION") == "current"
    assert values.get("BOARD_SUPER_PARTITION_METADATA_DEVICE") == "super"
    assert values.get("BOARD_SUPER_PARTITION_BLOCK_DEVICES") == "super"

def test_recovery_image_settings_and_dynamic_partitions():
    _, values, _ = load_parsed()
    assert values.get("BOARD_HAS_NO_REAL_SDCARD") == "true"
    assert values.get("BOARD_SUPPRESS_EMMC_WIPE") == "true"
    assert values.get("BOARD_SUPPRESS_LINEAGE_BUILDTYPE") == "true"
    assert values.get("TW_INCLUDE_FASTBOOTD") == "true"
    assert values.get("TW_USE_DYNAMIC_PARTITIONS") == "true"

def test_properties_and_kernel_config_references_exist():
    _, values, _ = load_parsed()
    # Ensure references are present as strings; we don't resolve paths here
    assert values.get("TARGET_SYSTEM_PROP") == "$(DEVICE_PATH)/system.prop"
    assert values.get("TARGET_KERNEL_CONFIG") == "ares_defconfig"

def test_common_failure_modes_helpfulness():
    """
    Intentionally verifies that the parser handles lines that don't match VAR :=|+= VALUE
    by ignoring them without throwing errors (e.g., comments, empty lines).
    """
    # Create a minimal sample and ensure parser does not explode
    sample = [
        "# comment only",
        "",
        "FOO := bar",
        "FOO += baz",
        "not a key line",
    ]
    values, accum = parse_boardconfig_lines(sample)
    assert values["FOO"] == "bar"
    assert combined_value(accum, "FOO") == "bar baz"