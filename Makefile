# PM Interview Panel — repo-root Makefile.
#
# Backend commands run through backend/.venv (created per PHASE-0-SPEC.md 0.1,
# Python 3.12). Frontend commands run through frontend/'s npm scripts. Targets
# mirror the "Commands" table in CLAUDE.md exactly — do not rename one without
# updating the other.

ifeq ($(OS),Windows_NT)
  VENV_PYTHON := .venv/Scripts/python.exe
else
  VENV_PYTHON := .venv/bin/python
endif

.PHONY: dev-api dev-web test test-api test-web golden

## FastAPI with reload, port 8000.
dev-api:
	cd backend && $(VENV_PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Vite dev server.
dev-web:
	cd frontend && npm run dev

## Everything: backend pytest + frontend vitest.
test: test-api test-web

## pytest only. Live tests hit the real GROQ endpoint (not NVIDIA — the provider
## moved 2026-07-31, see DEV-STATE § Decisions) and are marked @pytest.mark.live.
## Deselect with: make test-api PYTEST_ARGS="-m 'not live'"
##
## NOTE: `pytest tests` includes tests/golden/, so this target runs the eight
## Resume Analyst golden cases on `deep` too — about 32,000 tokens of a 200,000
## per-model DAILY budget. Use the `golden` target to run them deliberately, and
## PYTEST_ARGS="-m 'not live'" while iterating.
test-api:
	cd backend && $(VENV_PYTHON) -m pytest tests -v $(PYTEST_ARGS)

## vitest only.
test-web:
	cd frontend && npm test

## All agent golden cases: backend/tests/golden/<agent>/. Scope to one agent
## with AGENT=<name>. No agents exist yet in Phase 0 — this is a stable
## contract for Phase 1 onward, per CLAUDE.md "Golden cases must pass before
## any agent prompt change is committed."
golden:
ifdef AGENT
	cd backend && $(VENV_PYTHON) -m pytest tests/golden/$(AGENT) -v
else
	cd backend && $(VENV_PYTHON) -m pytest tests/golden -v
endif
