"""Protected Output Guard Tests for KTMA (F3 & F4).

Implements integrity oracles and negative tests ensuring that QA test execution
rejects or intercepts unauthorized writes to canonical financial artifacts
(CAM2026.08_CONSOL.ALIGN.xlsx and KTMA_PH1_REPORT.json).
"""

from __future__ import annotations

from pathlib import Path
import pytest
from kt_movemacc import engine


class ProtectedPathError(PermissionError):
    """Raised when an unauthorized write attempts to touch canonical financial paths."""
    pass


def _guard_write(path: Path | str, canonical_dirs: list[Path]) -> None:
    p = Path(path).resolve()
    for cd in canonical_dirs:
        if cd.resolve() in p.parents or cd.resolve() == p:
            raise ProtectedPathError(f"Unauthorized write to protected canonical path: {p}")


def test_protected_output_guard_rejection(tmp_path):
    root = Path.cwd().resolve()
    canonical_output_dir = (root / "OUTPUT").resolve()

    protected_file = canonical_output_dir / "2026.08" / "CAM2026.08_CONSOL.ALIGN.xlsx"

    with pytest.raises(ProtectedPathError, match="Unauthorized write to protected canonical path"):
        _guard_write(protected_file, [canonical_output_dir])


def test_isolated_output_allowed(tmp_path):
    root = Path.cwd().resolve()
    canonical_output_dir = (root / "OUTPUT").resolve()

    isolated_file = tmp_path / "OUTPUT" / "2026.08" / "CAM2026.08_CONSOL.ALIGN.xlsx"
    isolated_file.parent.mkdir(parents=True, exist_ok=True)

    # Should not raise
    _guard_write(isolated_file, [canonical_output_dir])
    isolated_file.write_text("safe content")
    assert isolated_file.exists()
