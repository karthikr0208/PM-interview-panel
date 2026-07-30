"""Shared fixtures. Only fixtures with a real caller live here — see CLAUDE.md.

`tests/__init__.py` makes this directory a package with no `__init__.py`
above it (backend/ has none), so pytest's import machinery inserts
backend/ into sys.path[0]. That is what lets `from app.config import ...`
resolve cleanly in every test module without a per-file sys.path hack.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"


@pytest.fixture
def import_config_subprocess() -> Callable[[dict[str, str]], "subprocess.CompletedProcess[str]"]:
    """Runs `import app.config` in a fresh child process, with `overrides`
    layered on top of the current environment.

    A child process is required — config.py validates os.environ at import
    time (module level), so simulating "this variable is absent" needs a
    process where it is genuinely absent going in. Setting it to "" in the
    child's environment does that without touching the real backend/.env:
    `_read_required()` treats a blank string as missing, and
    `load_dotenv(override=False)` never repopulates a key the child's
    environment already contains, empty or not.
    """

    def run(overrides: dict[str, str]) -> "subprocess.CompletedProcess[str]":
        env = {**os.environ, **overrides}
        return subprocess.run(
            [str(VENV_PYTHON), "-c", "import app.config"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    return run
