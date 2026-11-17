# CLAUDE.md — clif-epi-hypophosphatemia

## Start here
- **`TASK.md` is the researcher's brief and the authority on scope.** Read it first. Never create or
  edit it. Propose changes and let the researcher make them.
- Decisions and their rationale (local only, gitignored): `.claude/claude-progress.md` (D1…). Plan: `.claude/claude-todo.md`.
  Lessons: `.claude/lessons.md`.
- CLIF 3.0 field and vocabulary evidence: `docs/clif_3_0_spec_check.md`.

## Architecture
- Python 01–03 build a one-row-per-patient analytic dataset. R 04 onward reads it from
  `output/intermediate_phi/` as parquet.
- `code/clif_load.py` exposes CLIF tables as DuckDB views using the names in
  `config/definitions.yaml`. Steps query the views in SQL. Session time zone is UTC.
- Every threshold, window and vocabulary value lives in `config/definitions.yaml`, never in code.
  Add a key only together with the step that reads it: the test fails on an unread key.
- `clif_spec_ref` pins CLIF 3.0 to a branch commit. 3.0 is unreleased, so re-check vocabularies
  before re-pinning.

## CLIF 3.0 pitfalls
- Values are lowercase snake_case (`imv`, `room_air`, `expired`, `mg/dl`). 2.1 spellings match nothing.
- The RRT table is `renal_replacement_therapy` (`mode_category`), but clifpy and synthetic_clif still
  use `crrt_therapy`. Net ultrafiltration moved to `output`.
- `labs.creatinine` covers several specimens: filter `lab_specimen_category = plasma_blood`.
- clifpy (all versions) can't load the 3.0 RRT, airway or mcs tables. Its waterfall hardcodes 2.1
  spellings. Don't use clifpy for 3.0 tables; the respiratory waterfall is being ported (D16).

## Data safety and execution
- Never read real data or anything under `output/intermediate_phi/`, and never run code in this
  folder: the execution guard blocks it. Hand the researcher the exact command.
- Synthetic tests are safe for the researcher to run via `!`:
  `cd ~/Desktop/Research/CLIF/CRRT/hypophosphatemia/clif-epi-hypophosphatemia && .venv/bin/python tests/test_01_cohort.py`
- Real runs happen in the researcher's own Terminal, and only once this site has CLIF 3.0 tables.
  `config/config.json` stays at 2.1.0 until then, and the pipeline refuses to run on it.
- Keep handed-over command lines short. Long lines wrap when copied and break.
