"""TASK066 real-entrypoint regression lab for RI-01 through RI-18."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "07_TOOLS" / "ktma_root_guard.py"
LAB = ROOT / "08_EVIDENCE" / "TASK067_ROOT_AUTHORITY_LAB" / "TASK066_REGRESSION_RUN_002"
AUTHORIZED = LAB / "authorized_project"
EXTERNAL = LAB / "external_protected_project"
EVIDENCE = ROOT / "08_EVIDENCE" / "REPORTS" / "KTMA_TASK067_TASK066_REGRESSION_RUN_002.jsonl"


def _wsl(path: Path) -> str:
    resolved = path.resolve(strict=False)
    if os.name != "nt":
        return resolved.as_posix()
    drive = resolved.drive[0].lower()
    remainder = resolved.as_posix()[2:]
    return f"/mnt/{drive}{remainder}"


def _context(
    *,
    root: Path = ROOT,
    operations: tuple[str, ...],
    allowlist: tuple[Path | str, ...],
    indirect: tuple[Path | str, ...] = (),
    external_roots: tuple[Path | str, ...] = (EXTERNAL,),
    runtime: str = "windows" if os.name == "nt" else "wsl2",
) -> dict:
    return {
        "ACTIVE_PROJECT": "KT.MovemAcc",
        "AUTHORIZED_ROOT": str(root),
        "TASK_ID": "KTMA_TASK066_PROJECT_ROOT_ENFORCEMENT",
        "AUTHORIZED_OPERATIONS": list(operations),
        "EXACT_TARGET_ALLOWLIST": [str(item) for item in allowlist],
        "EXECUTION_RUNTIME": runtime,
        "DECLARED_INDIRECT_OUTPUTS": [str(item) for item in indirect],
        "EXTERNAL_REPOSITORY_ROOTS": [str(item) for item in external_roots],
    }


def _run(context: dict, *arguments: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    command = [
        sys.executable,
        str(TOOL),
        "--authorization-json",
        json.dumps(context, separators=(",", ":")),
        *arguments,
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT / "src")},
    )
    output = completed.stdout.strip().splitlines()
    payload = json.loads(output[-1]) if output else {"status": "NO_OUTPUT", "stderr": completed.stderr}
    return completed, payload


def _record(
    test_id: str,
    input_value: str,
    expected: str,
    completed: subprocess.CompletedProcess[str],
    payload: dict,
    passed: bool,
    side_effects: str,
) -> dict:
    return {
        "TEST_ID": test_id,
        "INPUT": input_value,
        "ENTRYPOINT": "07_TOOLS/ktma_root_guard.py",
        "EXPECTED": expected,
        "OBSERVED": {"exit_code": completed.returncode, "payload": payload},
        "RESULT": "PASS" if passed else "FAIL",
        "SIDE_EFFECTS": side_effects,
        "EVIDENCE": payload.get("code", "NO_CODE"),
    }


def _snapshot_files(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            snapshot[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            # An inaccessible adversarial reparse point is not followed.
            continue
    return snapshot


def _create_directory_link(link: Path, target: Path) -> None:
    """Create a contained directory escape fixture using the available Windows primitive."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError as exc:
        if os.name != "nt" or getattr(exc, "winerror", None) != 1314:
            raise
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def _create_file_link(link: Path, target: Path) -> bool:
    try:
        os.symlink(target, link)
        return True
    except OSError as exc:
        if os.name != "nt" or getattr(exc, "winerror", None) != 1314:
            raise
    completed = subprocess.run(
        ["wsl.exe", "--exec", "ln", "-s", _wsl(target), _wsl(link)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def test_task066_ri_01_through_ri_18_real_entrypoint():
    assert not LAB.exists(), f"Fixture collision: {LAB}"
    assert not EVIDENCE.exists(), f"Evidence collision: {EVIDENCE}"
    AUTHORIZED.mkdir(parents=True)
    EXTERNAL.mkdir(parents=True)
    (AUTHORIZED / "IDEAS").mkdir()
    records: list[dict] = []

    # RI-01: protected external project write.
    target = EXTERNAL / "ri01.txt"
    cp, payload = _run(
        _context(operations=("create",), allowlist=(target,)),
        "write-text", "--target", str(target), "--resolved-target", str(target), "--text", "blocked",
    )
    records.append(_record("RI-01", str(target), "DENIED", cp, payload, cp.returncode == 3 and not target.exists(), "no external file created"))

    # RI-02: create outside the authorized project without relying on repo classification.
    target = ROOT.parent / "KTMA_TASK067_EXTERNAL_SIMULATION" / "ri02.txt"
    cp, payload = _run(
        _context(operations=("create",), allowlist=(target,), external_roots=()),
        "write-text", "--target", str(target), "--resolved-target", str(target), "--text", "blocked",
    )
    records.append(_record("RI-02", str(target), "DENIED", cp, payload, cp.returncode == 3 and not target.exists(), "no outside file created"))

    # RI-03: delete outside the authorized project.
    target = EXTERNAL / "delete_me.txt"
    target.write_text("preserve", encoding="utf-8")
    cp, payload = _run(
        _context(operations=("delete",), allowlist=(target,)),
        "delete", "--target", str(target), "--resolved-target", str(target),
    )
    records.append(_record("RI-03", str(target), "DENIED", cp, payload, cp.returncode == 3 and target.read_text(encoding="utf-8") == "preserve", "external source preserved"))

    # RI-04: move across project boundary.
    source = AUTHORIZED / "move_source.txt"
    destination = EXTERNAL / "move_destination.txt"
    source.write_text("move-source", encoding="utf-8")
    cp, payload = _run(
        _context(operations=("move",), allowlist=(source, destination)),
        "move", "--source", str(source), "--resolved-source", str(source), "--target", str(destination), "--resolved-target", str(destination),
    )
    records.append(_record("RI-04", f"{source} -> {destination}", "DENIED", cp, payload, cp.returncode == 3 and source.exists() and not destination.exists(), "source preserved; destination absent"))

    # RI-05: copy across project boundary.
    source = AUTHORIZED / "copy_source.txt"
    destination = EXTERNAL / "copy_destination.txt"
    source.write_text("copy-source", encoding="utf-8")
    cp, payload = _run(
        _context(operations=("copy",), allowlist=(source, destination)),
        "copy", "--source", str(source), "--resolved-source", str(source), "--target", str(destination), "--resolved-target", str(destination),
    )
    records.append(_record("RI-05", f"{source} -> {destination}", "DENIED", cp, payload, cp.returncode == 3 and source.exists() and not destination.exists(), "source preserved; destination absent"))

    # RI-06: WSL mount path targets external project.
    target = EXTERNAL / "ri06.txt"
    wsl_target = _wsl(target)
    cp, payload = _run(
        _context(operations=("create",), allowlist=(target,), runtime="wsl2"),
        "write-text", "--target", wsl_target, "--resolved-target", str(target), "--text", "blocked",
    )
    records.append(_record("RI-06", wsl_target, "DENIED", cp, payload, cp.returncode == 3 and not target.exists(), "no WSL-mapped external file created"))

    # RI-07: direct file-symlink escape (Windows API, then native WSL fallback).
    symlink_target = EXTERNAL / "symlink_target.txt"
    symlink_target.write_text("external", encoding="utf-8")
    link = AUTHORIZED / "link_file"
    if _create_file_link(link, symlink_target):
        cp, payload = _run(
            _context(operations=("overwrite",), allowlist=(link,)),
            "write-text", "--target", str(link), "--resolved-target", str(symlink_target), "--text", "blocked",
        )
        records.append(_record("RI-07", str(link), "DENIED", cp, payload, cp.returncode == 3 and symlink_target.read_text(encoding="utf-8") == "external", "direct file-symlink target preserved"))
    else:
        records.append({
            "TEST_ID": "RI-07",
            "INPUT": str(link),
            "ENTRYPOINT": "NOT_EXECUTED_NO_FILE_SYMLINK_FIXTURE",
            "EXPECTED": "DENIED",
            "OBSERVED": {"status": "BLOCKED", "code": "FILE_SYMLINK_CAPABILITY_UNAVAILABLE"},
            "RESULT": "BLOCKED",
            "SIDE_EFFECTS": "no link or target mutation",
            "EVIDENCE": "Windows privilege and WSL fallback unavailable",
        })

    # RI-08: directory symlink/reparse escape.
    link_dir = AUTHORIZED / "link_dir"
    _create_directory_link(link_dir, EXTERNAL)
    target = link_dir / "ri08.txt"
    resolved_target = EXTERNAL / "ri08.txt"
    cp, payload = _run(
        _context(operations=("create",), allowlist=(target,)),
        "write-text", "--target", str(target), "--resolved-target", str(resolved_target), "--text", "blocked",
    )
    records.append(_record("RI-08", str(target), "DENIED", cp, payload, cp.returncode == 3 and not resolved_target.exists(), "reparse target absent"))

    # RI-09: git -C points to external repository.
    internal_output = AUTHORIZED / "git_output.txt"
    command = ["git", "-C", str(EXTERNAL), "add", "x"]
    cp, payload = _run(
        _context(operations=("git",), allowlist=(internal_output,)),
        "validate-command", "--cwd", str(AUTHORIZED), "--command-json", json.dumps(command),
    )
    records.append(_record("RI-09", " ".join(command), "DENIED", cp, payload, cp.returncode == 3, "git command not executed"))

    # RI-10: git alternate work tree / git dir.
    command = ["git", f"--work-tree={EXTERNAL}", f"--git-dir={EXTERNAL / '.git'}", "add", "x"]
    cp, payload = _run(
        _context(operations=("git",), allowlist=(internal_output,)),
        "validate-command", "--cwd", str(AUTHORIZED), "--command-json", json.dumps(command),
    )
    records.append(_record("RI-10", " ".join(command), "DENIED", cp, payload, cp.returncode == 3, "git command not executed"))

    # RI-11: hidden external output differs from declared output.
    hidden = EXTERNAL / "hidden.log"
    cp, payload = _run(
        _context(operations=("git",), allowlist=(internal_output, hidden)),
        "validate-command", "--cwd", str(AUTHORIZED), "--command-json", json.dumps(["tool", "run"]),
        "--declared-output", str(internal_output), "--observed-output", str(hidden),
    )
    records.append(_record("RI-11", str(hidden), "DENIED", cp, payload, cp.returncode == 3 and not hidden.exists(), "hidden output absent"))

    # RI-12: delegated scope expansion.
    internal = AUTHORIZED / "delegated.txt"
    broader = EXTERNAL / "delegated_external.txt"
    cp, payload = _run(
        _context(operations=("create",), allowlist=(internal,)),
        "delegate-check", "--operations-json", json.dumps(["create"]), "--allowlist-json", json.dumps([str(internal), str(broader)]),
    )
    records.append(_record("RI-12", str(broader), "DENIED", cp, payload, cp.returncode == 3 and not broader.exists(), "delegated external target absent"))

    # RI-13: traversal.
    traversal = str(AUTHORIZED / "nested" / ".." / ".." / "external_protected_project" / "ri13.txt")
    cp, payload = _run(
        _context(operations=("create",), allowlist=(traversal,), external_roots=()),
        "write-text", "--target", traversal, "--resolved-target", str(EXTERNAL / "ri13.txt"), "--text", "blocked",
    )
    records.append(_record("RI-13", traversal, "DENIED", cp, payload, cp.returncode == 3 and not (EXTERNAL / "ri13.txt").exists(), "traversal destination absent"))

    # RI-14: private-use Unicode separators.
    malformed = "C\uf03a\uf05cUsers\uf05caazcl\uf05coutside.txt"
    cp, payload = _run(
        _context(operations=("create",), allowlist=(malformed,), external_roots=()),
        "write-text", "--target", malformed, "--resolved-target", malformed, "--text", "blocked",
    )
    records.append(_record("RI-14", malformed, "DENIED", cp, payload, cp.returncode == 3, "no malformed path created"))

    # RI-15: false string-prefix sibling.
    prefix_sibling = Path(f"{ROOT}-Other") / "ri15.txt"
    cp, payload = _run(
        _context(operations=("create",), allowlist=(prefix_sibling,), external_roots=()),
        "write-text", "--target", str(prefix_sibling), "--resolved-target", str(prefix_sibling), "--text", "blocked",
    )
    records.append(_record("RI-15", str(prefix_sibling), "DENIED", cp, payload, cp.returncode == 3 and not prefix_sibling.exists(), "prefix-sibling destination absent"))

    # RI-16: actual unexpected post-write fixture effect.
    expected_file = AUTHORIZED / "expected.txt"
    unexpected_file = AUTHORIZED / "unexpected.txt"
    before = _snapshot_files(AUTHORIZED)
    expected_file.write_text("expected", encoding="utf-8")
    unexpected_file.write_text("unexpected", encoding="utf-8")
    after = _snapshot_files(AUTHORIZED)
    expected_path = str(expected_file.resolve())
    unexpected_path = str(unexpected_file.resolve())
    cp, payload = _run(
        _context(operations=("verify",), allowlist=(Path(expected_path), Path(unexpected_path))),
        "verify-delta", "--before-json", json.dumps(before), "--after-json", json.dumps(after), "--allowed-json", json.dumps([expected_path]),
    )
    records.append(_record("RI-16", unexpected_path, "DENIED", cp, payload, cp.returncode == 3, "unexpected effect detected from actual fixture snapshots"))

    # RI-17: timeout/uncertain effect cannot be retried blindly.
    uncertain_target = str(AUTHORIZED / "uncertain.txt")
    cp, payload = _run(
        _context(operations=("verify",), allowlist=(Path(uncertain_target),)),
        "incident", "--target", uncertain_target, "--reason", "simulated timeout after dispatch",
    )
    records.append(_record("RI-17", uncertain_target, "UNCERTAIN_EFFECT", cp, payload, cp.returncode == 4 and payload.get("status") == "UNCERTAIN_EFFECT" and payload.get("evidence", {}).get("retry_allowed") is False, "no retry and no write performed"))

    # RI-18: valid allowlisted write under simulated project IDEAS.
    target = AUTHORIZED / "IDEAS" / "valid.txt"
    cp, payload = _run(
        _context(operations=("create",), allowlist=(target,)),
        "write-text", "--target", str(target), "--resolved-target", str(target), "--text", "authorized\n",
    )
    expected_hash = hashlib.sha256(b"authorized\n").hexdigest()
    passed = cp.returncode == 0 and target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected_hash
    records.append(_record("RI-18", str(target), "VERIFIED", cp, payload, passed, "one exact allowlisted file created"))

    evidence_text = "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in records)
    evidence_context = _context(
        root=ROOT,
        operations=("create",),
        allowlist=(EVIDENCE,),
        external_roots=(),
    )
    evidence_cp, evidence_payload = _run(
        evidence_context,
        "write-text", "--target", str(EVIDENCE), "--resolved-target", str(EVIDENCE), "--text", evidence_text,
    )
    assert evidence_cp.returncode == 0, evidence_payload
    assert len(records) == 18
    assert not any(record["RESULT"] == "FAIL" for record in records), records
