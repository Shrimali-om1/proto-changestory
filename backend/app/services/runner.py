from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from app.models import Verification


SAMPLE_ROOT = Path(__file__).resolve().parents[3] / "sample-project"
COMMAND = [sys.executable, "-m", "pytest", "-q"]


def run_controlled_tests() -> Verification:
    """Run exactly the predefined test command in the bundled sample project."""
    started = time.perf_counter()
    try:
        result = subprocess.run(COMMAND, cwd=SAMPLE_ROOT, text=True, capture_output=True, timeout=30, shell=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return Verification(status="error", duration_seconds=round(time.perf_counter() - started, 3), passed=[], failed=[], summary=f"Controlled verification could not run: {error}")
    output = (result.stdout + "\n" + result.stderr).strip()
    status = "passed" if result.returncode == 0 else "failed"
    return Verification(status=status, duration_seconds=round(time.perf_counter() - started, 3),
                        passed=[output] if status == "passed" else [], failed=[output] if status == "failed" else [],
                        summary="Bundled sample-project tests passed." if status == "passed" else "Bundled sample-project tests failed.")
