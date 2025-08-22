from pathlib import Path

import pytest

# Attempt to import yaml if available; tests that need parsing will xfail if not present.
try:
    import yaml  # PyYAML
    HAS_YAML = True
except Exception:
    HAS_YAML = False

def _load_workflow_text():
    """
    Locate the workflow file containing the 'TWRP Recovery Builder' workflow.
    Prefer files under .github/workflows. Fallback to searching repo.
    """
    candidates = []
    root = Path(__file__).resolve().parents[1]
    workflows_dir = root / ".github" / "workflows"
    if workflows_dir.is_dir():
        for p in workflows_dir.glob("*.y*ml"):
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if "TWRP Recovery Builder" in txt or "platform_manifest_twrp_aosp" in txt:
                candidates.append((p, txt))
    # Fallback: search entire repo for unique markers from the diff
    if not candidates:
        for p in root.rglob("*.y*ml"):
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if "TWRP Recovery Builder" in txt or "platform_manifest_twrp_aosp" in txt:
                candidates.append((p, txt))
    if not candidates:
        pytest.skip("Could not locate the workflow YAML file; ensure it exists in .github/workflows.")
    # If multiple, pick the one with the strongest signature
    candidates.sort(key=lambda item: (
        ("TWRP Recovery Builder" in item[1]) +
        ("softprops/action-gh-release@v1" in item[1]) +
        ("haya14busa/action-cond@v1" in item[1])
    ), reverse=True)
    return candidates[0]

def _yaml_or_text():
    p, txt = _load_workflow_text()
    data = None
    if HAS_YAML:
        try:
            data = yaml.safe_load(txt)
        except Exception as e:
            # Provide helpful context in failure
            pytest.fail(f"Workflow YAML failed to parse with PyYAML: {e}")
    return p, txt, data

def test_workflow_file_present_and_named():
    p, txt = _load_workflow_text()
    # Basic presence checks
    assert p.exists(), "Workflow file should exist"
    assert p.suffix in {".yml", ".yaml"}, "Workflow should be a YAML file"
    # Strong signature from diff
    assert "TWRP Recovery Builder" in txt, "Workflow should contain the expected name"

@pytest.mark.parametrize("expected_action", [
    "actions/checkout@v4",
    "rokibhasansagar/slimhub_actions@main",
    "pierotofy/set-swap-space@master",
    "actions/setup-java@v4",
    "haya14busa/action-cond@v1",
    "softprops/action-gh-release@v1",
])
def test_critical_actions_are_referenced(expected_action):
    _, txt, _ = _yaml_or_text()
    assert expected_action in txt, f"Expected action '{expected_action}' not found in workflow"

def test_runs_on_and_job_name_and_if_condition():
    p, txt, data = _yaml_or_text()
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; structure checks require PyYAML")
    # Validate jobs.build structure
    jobs = data.get("jobs") or {}
    build = jobs.get("build") or {}
    assert build.get("name") and "TWRP" in build.get("name"), "Job name should reference TWRP"
    assert build.get("runs-on") == "ubuntu-latest", "runs-on should be ubuntu-latest"
    assert build.get("if") == "github.event.repository.owner.id == github.event.sender.id", "Job-level if condition should match diff"

def test_env_and_permissions():
    _, _, data = _yaml_or_text()
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; structure checks require PyYAML")
    env = (data.get("jobs") or {}).get("build", {}).get("env") or {}
    assert "GITHUB_TOKEN" in env and "${{ secrets.GITHUB_TOKEN }}" in env["GITHUB_TOKEN"]
    assert env.get("BUILD_AUTHOR") == "ツ๛abrohim๛"
    perms = (data.get("jobs") or {}).get("build", {}).get("permissions") or {}
    assert perms.get("contents") == "write", "Release publishing requires contents: write"

def test_workflow_dispatch_inputs_core_defaults_and_types():
    _, _, data = _yaml_or_text()
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; structure checks require PyYAML")
    on = data.get("on") or {}
    wd = (on.get("workflow_dispatch") or {})
    inputs = wd.get("inputs") or {}
    # MANIFEST_BRANCH
    mb = inputs.get("MANIFEST_BRANCH") or {}
    assert mb.get("required") is True
    assert mb.get("default") == "twrp-12.1"
    assert mb.get("type") == "choice"
    assert sorted(mb.get("options") or []) == sorted(["twrp-14.1","twrp-12.1","twrp-11","twrp-9.0"])
    # DEVICE_TREE
    dt = inputs.get("DEVICE_TREE") or {}
    assert dt.get("required") is True
    assert dt.get("default") == "https://github.com/abrohim0786/F3GT-twrp-tree.git"
    # DEVICE_TREE_BRANCH
    dtb = inputs.get("DEVICE_TREE_BRANCH") or {}
    assert dtb.get("required") is True
    assert dtb.get("default") == ""
    # DEVICE_PATH
    dpath = inputs.get("DEVICE_PATH") or {}
    assert dpath.get("required") is True and dpath.get("default") == "device/xiaomi/ares"
    # DEVICE_NAME
    dname = inputs.get("DEVICE_NAME") or {}
    assert dname.get("required") is True and dname.get("default") == "ares"
    # BUILD_TARGET
    bt = inputs.get("BUILD_TARGET") or {}
    assert bt.get("required") is True
    assert bt.get("default") == "boot"
    assert bt.get("type") == "choice"
    assert sorted(bt.get("options") or []) == sorted(["boot","recovery","vendorboot"])
    # LDCHECK
    ldc = inputs.get("LDCHECK") or {}
    assert ldc.get("required") is True and ldc.get("default") == "system/bin/qseecomd"
    # RECOVERY_INSTALLER
    ri = inputs.get("RECOVERY_INSTALLER") or {}
    assert ri.get("required") is True and ri.get("type") == "boolean" and ri.get("default") is True

def test_manifest_cond_includes_all_known_branches():
    _, txt, data = _yaml_or_text()
    # Text-level assertion (does not require YAML) to ensure 'twrp-14.1' is included
    assert "twrp-14.1" in txt, "Expected 'twrp-14.1' to be present in manifest options/conditions"
    # If YAML is available, drill into steps and verify haya14busa/action-cond cond
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; step-level condition checks require PyYAML")
    steps = (data.get("jobs") or {}).get("build", {}).get("steps") or []
    # Find the step with id: manifest
    manifest_steps = [s for s in steps if s.get("id") == "manifest"]
    assert manifest_steps, "Expected a step with id 'manifest'"
    cond = (manifest_steps[0].get("with") or {}).get("cond") or ""
    assert "twrp-11" in cond and "twrp-12.1" in cond and "twrp-14.1" in cond, "Manifest selection condition should include all branches per diff"

def test_python2_install_step_condition_is_not_outdated():
    """
    The diff shows 'Install Python 2 (Legacy Branches)' step guarded by a condition.
    Validate that the condition uses 'twrp-14.1' (not an outdated 'twrp-14').
    If it does not, this test should fail to signal the mismatch.
    """
    _, txt, data = _yaml_or_text()
    # Quick text check for potential bug: 'twrp-14' without '.1'
    assert "twrp-14.1" in txt, "Expect to see 'twrp-14.1' referenced in conditions or options."
    # YAML-level search through steps for 'Install Python 2'
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; step-level condition checks require PyYAML")
    steps = (data.get("jobs") or {}).get("build", {}).get("steps") or []
    legacy = [s for s in steps if isinstance(s.get("name"), str) and "Install Python 2" in s.get("name")]
    assert legacy, "Expected 'Install Python 2 (Legacy Branches)' step to exist"
    legacy_if = legacy[0].get("if", "")
    # Expect the condition to reference 'twrp-14.1' (not 'twrp-14' without patch version)
    assert "twrp-14.1" in legacy_if or "twrp-14" not in legacy_if, (
        "Legacy Python2 condition appears to reference 'twrp-14' instead of 'twrp-14.1'. "
        "Update the 'if' expression to consistently use 'twrp-14.1'."
    )

def test_release_step_includes_expected_files_and_metadata():
    _, _, data = _yaml_or_text()
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; structure checks require PyYAML")
    steps = (data.get("jobs") or {}).get("build", {}).get("steps") or []
    release = [s for s in steps if (s.get("uses") or "").startswith("softprops/action-gh-release")]
    assert release, "Expected a GitHub Release step using softprops/action-gh-release@v1"
    with_ = release[0].get("with") or {}
    files = with_.get("files") or ""
    assert "workspace/out/target/product/${{ github.event.inputs.DEVICE_NAME }}/${{ env.RECOVERY_FILE }}" in files
    assert "workspace/out/target/product/${{ github.event.inputs.DEVICE_NAME }}/recovery-installer.zip" in files
    assert "${{ env.MD5_IMG }}" in (with_.get("body") or ""), "Release body should include MD5 of the image"
    assert "${{ env.RECOVERY_TYPE }}" in (with_.get("name") or "")
    assert "${{ github.event.inputs.DEVICE_NAME }}" in (with_.get("tag_name") or "")

def test_locate_output_files_step_covers_boot_variants_and_errors():
    _, txt, _ = _yaml_or_text()
    # Pure text checks verify the three image variants and error path are present
    for variant in ["recovery.img", "boot.img", "vendor_boot.img"]:
        assert variant in txt, f"Expected {variant} handling in output locator step"
    assert "::error::No recovery file found in output directory!" in txt, "Should emit error when no output image exists"

def test_dependency_check_step_invokes_ldcheck_with_inputs():
    _, txt, _ = _yaml_or_text()
    assert "python3 ldcheck -p system/lib64:vendor/lib64:system/lib:vendor/lib -d ${{ github.event.inputs.LDCHECK }}" in txt, \
        "ldcheck should be invoked with library paths and the input LDCHECK path"

def test_swap_space_and_java_configuration():
    _, _, data = _yaml_or_text()
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; structure checks require PyYAML")
    steps = (data.get("jobs") or {}).get("build", {}).get("steps") or []
    # set-swap-space step
    swap_steps = [s for s in steps if (s.get("uses") or "").startswith("pierotofy/set-swap-space")]
    assert swap_steps, "Missing swap space step"
    assert (swap_steps[0].get("with") or {}).get("swap-size-gb") in (24, "24"), "Swap size should be 24 GB"
    # setup-java step
    java_steps = [s for s in steps if (s.get("uses") or "").startswith("actions/setup-java")]
    assert java_steps, "Missing setup-java step"
    with_java = java_steps[0].get("with") or {}
    assert with_java.get("distribution") == "zulu"
    assert str(with_java.get("java-version")) in {"8", "8.0", "8.x"}

def test_manifest_source_urls_for_true_false_paths_present():
    _, _, data = _yaml_or_text()
    if not HAS_YAML or not isinstance(data, dict):
        pytest.xfail("PyYAML not available or YAML not parsed; structure checks require PyYAML")
    steps = (data.get("jobs") or {}).get("build", {}).get("steps") or []
    cond_steps = [s for s in steps if (s.get("uses") or "").startswith("haya14busa/action-cond")]
    assert cond_steps, "Expected haya14busa/action-cond step"
    with_ = cond_steps[0].get("with") or {}
    assert "platform_manifest_twrp_aosp.git" in (with_.get("if_true") or "")
    assert "platform_manifest_twrp_omni.git" in (with_.get("if_false") or "")

def test_build_recovery_image_step_core_commands_present():
    _, txt, _ = _yaml_or_text()
    # Validate critical build commands appear in run script
    for token in [
        "source build/envsetup.sh",
        "ALLOW_MISSING_DEPENDENCIES=true",
        "lunch ${{ env.DEVICE_MAKEFILE }}-eng",
        "make clean",
        "make ${{ github.event.inputs.BUILD_TARGET }}image -j$(nproc --all)"
    ]:
        assert token in txt, f"Missing expected build command: {token}"

def test_add_recovery_installer_conditional_and_zip_update():
    _, txt, _ = _yaml_or_text()
    # Ensure step is gated by RECOVERY_INSTALLER input and performs zip update
    assert "if: ${{ github.event.inputs.RECOVERY_INSTALLER }}" in txt
    assert "recovery-installer.zip" in txt
    assert "zip -ur recovery-installer.zip ${{ env.RECOVERY_FILE }}" in txt

def test_device_tree_url_normalization_and_metadata_vars():
    _, txt, _ = _yaml_or_text()
    # Text checks suffice for bash logic applied in Set Build Metadata step
    assert 'if [[ "${DEVICE_TREE_URL}" == *.git ]]' in txt
    assert 'DEVICE_TREE_URL="${DEVICE_TREE_URL%.git}"' in txt
    for var in ["BUILD_DATE", "BUILD_TIME", "COMMIT_ID"]:
        assert f"${{{{ env.{var} }}}}" in txt, f"Expected env var {var} to be used in subsequent steps"