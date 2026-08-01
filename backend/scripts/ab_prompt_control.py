"""Validate an UNCOMMITTED prompt change against its committed control,
ALTERNATING, on a flapping golden case.

    backend/.venv/Scripts/python.exe backend/scripts/ab_prompt_control.py \
        [case_id] [pairs] [role]

    defaults: 01_apm_rotational  4  deep        cost: 2 x pairs calls

This is the method required by DEV-STATE § Decisions 2026-08-01 (session 7)
for any prompt change aimed at a case that flaps. Four consecutive green runs
on a 50/50 case is p = 0.06 by chance and has already produced one false pass
in this project.

Four rules it exists to enforce:
  1. the control is the COMMITTED prompt, read byte-exact from `git show HEAD:`,
     never reconstructed by string surgery
  2. the arms ALTERNATE, so serving drift over the hour hits both equally
  3. the real per-case check from cases.py runs, not just the one field you
     expect to move
  4. THE CONTROL MUST FAIL. If it does not, the run measured nothing and the
     change is unvalidated however clean the fix arm looks.

Requires the working tree to differ from HEAD; it aborts otherwise.
"""
from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
AGENT_REL = "backend/app/agents/resume_analyst.py"

PACE_SECONDS = 60


def load_head_module(head_path: Path):
    spec = importlib.util.spec_from_file_location("head_resume_analyst", head_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def head_prompt_module():
    """The committed agent module, materialised from git rather than rebuilt."""
    src = subprocess.run(
        ["git", "show", f"HEAD:{AGENT_REL}"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    tmp = Path(tempfile.mkdtemp()) / "head_resume_analyst.py"
    tmp.write_text(src, encoding="utf-8")
    return load_head_module(tmp)


async def main(case_id: str, n_pairs: int, role: str) -> int:
    sys.path.insert(0, str(BACKEND))

    from app.agents import resume_analyst as ra
    from tests.golden.resume_analyst.cases import CASES

    case = next(c for c in CASES if c.id == case_id)
    resume_text = case.resume_text

    FIX = ra._SYSTEM_PROMPT
    CONTROL = head_prompt_module()._SYSTEM_PROMPT

    if FIX == CONTROL:
        print("ABORT: working tree prompt is identical to HEAD. Nothing to A/B.")
        return 2

    print(f"prompt chars   FIX={len(FIX)}  CONTROL={len(CONTROL)}  delta={len(FIX)-len(CONTROL)}")
    print(f"case           {case.id}  role={role}")
    print(f"fixture        {case.fixture}  ({len(resume_text)} chars)")
    print(f"pacing         {PACE_SECONDS}s between calls\n")
    print(f"{'#':>2} {'variant':<8} {'level':<10} {'low_confidence_fields':<28} verdict")
    print("-" * 74)

    tally = {"FIX": [0, 0], "CONTROL": [0, 0]}  # [pass, fail]
    n = 0
    # CONTROL first: one FIX observation already exists from the pytest run, and
    # if the daily quota dies mid-probe an alternating order still leaves a
    # balanced sample rather than four of one arm and none of the other.
    for i in range(n_pairs):
        for label, prompt in (("CONTROL", CONTROL), ("FIX", FIX)):
            n += 1
            ra._SYSTEM_PROMPT = prompt
            try:
                result = await ra.analyse_resume(resume_text, role=role)
            except Exception as exc:  # noqa: BLE001 - classification is the point
                msg = str(exc)
                print(f"{n:>2} {label:<8} ERROR: {msg[:200]}")
                if "tokens per day" in msg or "TPD" in msg:
                    print("\nSTOP: daily token quota exhausted.")
                    return 3
                if "tokens per minute" in msg:
                    print("  (TPM - pacing too short)")
                await asyncio.sleep(PACE_SECONDS)
                continue

            lcf = result.low_confidence_fields
            try:
                case.check(result)
                verdict = "PASS"
                tally[label][0] += 1
            except AssertionError as exc:
                verdict = f"FAIL  {str(exc).splitlines()[0][:60]}"
                tally[label][1] += 1
            print(f"{n:>2} {label:<8} {result.assessed_level:<10} {str(lcf):<28} {verdict}")
            await asyncio.sleep(PACE_SECONDS)

    print("\n" + "=" * 74)
    for label, (p, f) in tally.items():
        print(f"{label:<8} pass={p} fail={f}")

    # Rule 4, enforced rather than trusted to the reader. A control that never
    # failed means the flap did not occur during this run, so the fix arm being
    # clean says nothing at all -- this is exactly how 2026-08-01's false pass
    # on `fast` was produced, and it read as a 5/5 success at the time.
    fix_pass, fix_fail = tally["FIX"]
    ctl_pass, ctl_fail = tally["CONTROL"]
    print()
    if ctl_fail == 0:
        print("INCONCLUSIVE: the control never failed, so this run measured nothing.")
        print("Do NOT record the fix as validated. Re-run when the case is flapping,")
        print("or confirm the flap still exists on this model before spending more budget.")
        return 4
    if fix_fail > 0:
        print(f"NOT VALIDATED: the fix arm failed {fix_fail} time(s).")
        return 5
    print(f"VALIDATED: fix {fix_pass}/{fix_pass}, control failed {ctl_fail}/{ctl_pass + ctl_fail}.")
    print("The control could fail and did, so the fix arm being clean is evidence.")
    return 0


if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else "01_apm_rotational"
    pairs = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    role = sys.argv[3] if len(sys.argv) > 3 else "deep"
    sys.exit(asyncio.run(main(case_id, pairs, role)))
