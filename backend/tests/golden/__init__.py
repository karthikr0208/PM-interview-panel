"""Golden-case fixtures and assertion harnesses, one subpackage per agent.

Sits under `tests/` (not a separate top-level dir) so pytest's existing
rootdir-relative import machinery picks it up for free -- see
`tests/conftest.py`'s docstring for why `tests/__init__.py` is what makes
`from app...` and `from tests...` resolve without a sys.path hack.
"""
