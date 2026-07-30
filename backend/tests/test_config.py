"""Phase 0 acceptance (PHASE-0-SPEC.md): "Missing env var raises an error
naming the variable." Also covers the two SUPABASE_DB_URL guards in
app/config.py: the transaction-pooler port and the non-pooler host.

Every case runs `import app.config` in a subprocess via the
`import_config_subprocess` fixture (see conftest.py) — config.py validates
os.environ at import time, so this is the only way to exercise "variable is
missing" without editing the real backend/.env.
"""
from __future__ import annotations

import pytest

from app.config import REQUIRED_VARS


@pytest.mark.parametrize("var_name", REQUIRED_VARS)
def test_missing_required_var_names_it(import_config_subprocess, var_name: str) -> None:
    result = import_config_subprocess({var_name: ""})

    assert result.returncode != 0, (
        f"import app.config should fail with {var_name} unset; it did not.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "ConfigError" in result.stderr
    assert var_name in result.stderr, (
        f"error message does not name {var_name}:\n{result.stderr}"
    )


def test_transaction_pooler_port_rejected(import_config_subprocess) -> None:
    """Port 6543 recycles connections between transactions and breaks the
    LangGraph checkpointer with DuplicatePreparedStatement. Must be caught at
    import time, not mid-interview."""
    bad_url = "postgresql://postgres.ref:pw@aws-ap-southeast-1.pooler.supabase.com:6543/postgres"
    result = import_config_subprocess({"SUPABASE_DB_URL": bad_url})

    assert result.returncode != 0
    assert "ConfigError" in result.stderr
    assert "6543" in result.stderr
    assert "transaction pooler" in result.stderr


def test_non_pooler_host_rejected(import_config_subprocess) -> None:
    """The direct connection (db.<ref>.supabase.co) is IPv6-only and
    unreachable from Render's free tier; catching "not a pooler host" also
    catches that case."""
    bad_url = "postgresql://postgres:pw@db.abcdefgh.supabase.co:5432/postgres"
    result = import_config_subprocess({"SUPABASE_DB_URL": bad_url})

    assert result.returncode != 0
    assert "ConfigError" in result.stderr
    assert "not a Supabase pooler host" in result.stderr
