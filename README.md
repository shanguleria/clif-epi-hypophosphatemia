# clif-epi-hypophosphatemia

Epidemiology of hypophosphatemia in adults receiving continuous renal replacement therapy (CRRT) in the ICU, built on CLIF.

## Objective

Describe the incidence and timing of hypophosphatemia (< 2.5 mg/dL) and severe hypophosphatemia
(< 1.5 mg/dL) after CRRT start, the characteristics of patients who develop it, phosphate repletion,
and clinical outcomes (IMV after CRRT start, VFD-28, extubation, tracheostomy, ICU LOS, in-hospital
mortality). The pipeline is **descriptive**. Python steps build a one-row-per-patient analytic
dataset, and R steps produce the descriptive tables and models.

## Required CLIF tables and fields

CLIF spec version: **3.0** (unreleased). Table and vocabulary names are pinned to branch `3.0` at
commit `3ee2e02` of `Common-Longitudinal-ICU-data-Format/CLIF` (`clif_spec_ref` in
`config/definitions.yaml`). CLIF 3.0 values are lowercase snake_case.

Used by `01_cohort`:

| Table | Fields | Categorical values used |
|---|---|---|
| `hospitalization` | `patient_id`, `hospitalization_id`, `admission_dttm`, `discharge_dttm`, `age_at_admission`, `discharge_category` | |
| `adt` | `hospitalization_id`, `in_dttm`, `out_dttm`, `location_category` | `location_category = icu`; `procedural`, `radiology` bridge ICU rows |
| `renal_replacement_therapy` | `hospitalization_id`, `recorded_dttm`, `mode_category` | `mode_category` ∈ {`cvvh`, `cvvhd`, `cvvhdf`} |
| `labs` | `hospitalization_id`, `lab_category`, `lab_value_numeric`, `lab_collect_dttm`, `lab_specimen_category` | `lab_category = phosphate`, `lab_specimen_category = plasma_blood` |

Steps 02–03 will add `patient`, `vitals`, `respiratory_support`, `airway`, `mcs`,
`medication_admin_continuous`, `medication_admin_intermittent`, `output` and `hospital_diagnosis`.
This table grows as those steps are written.

## Cohort identification

- **Population:** hospitalizations with `age_at_admission` ≥ 18.
- **Index:** each patient's earliest CRRT episode (`cvvh`/`cvvhd`/`cvvhdf`) whose first record falls
  within an ICU stay. Episodes are built from qualifying-mode records only, and a gap of 24 h or more
  starts a new episode. ICU stays are ICU `adt` rows merged across gaps of 6 h or less, or across a
  gap of any length spent only in `procedural` or `radiology` locations. **t0** is the episode's
  first record.
- **Unit of analysis:** one row per patient. This is the patient's first hospitalization with CRRT
  started in the ICU, and the ICU stay in which it started.
- **Outcome windows:**
  - *Phosphate outcomes* (hypophosphatemia incidence, repletion): t0 to the earliest of CRRT end +
    48 h, ICU-stay end and hospital discharge (`phosphate_window_end`).
  - *Longer-term outcomes* (mortality, extubation, tracheostomy): t0 to the earlier of t0 + 28 days
    and hospital discharge (`followup_end`). In-hospital death is a discharge.
- **Exclusion:** any `plasma_blood` phosphate < 2.5 mg/dL collected in the 72 h before t0. Patients
  with no phosphate in that window are kept and flagged (`has_baseline_phosphate = false`).
- **Outputs:** patient-level parquet in `output/intermediate_phi/`. In `output/final_no_phi/`:
  small-cell-suppressed CSV counts, a provenance JSON per step, and logs.

All thresholds, windows and vocabularies live in `config/definitions.yaml`. Every key in that file is
read by some step, and `tests/test_01_cohort.py` fails if one is not.

## Configuration

```bash
cp config/config.example.json config/config.json
```

Edit `config/config.json`:

| Key | Meaning |
|---|---|
| `site` | Site identifier written into shareable outputs |
| `data_directory` | Absolute path to this site's CLIF tables (`clif_<table>.<filetype>`) |
| `filetype` | `parquet` or `csv` |
| `timezone` | Site timezone. Used to localize `*_dttm` columns stored without a timezone |
| `clif_version` | CLIF **spec** version of the site's tables. Must be 3.x: the pipeline refuses other major versions |
| `small_cell_threshold` | Counts from 1 to this value minus 1 are suppressed, and they block a `git push` |
| `redact_site_names` | Names that must never appear in pushed files (pre-push check) |
| `dataset_version` | *Optional.* ETL or dataset release, recorded in provenance |
| `output_root` | *Optional.* Output folder, relative to the config file. Default: the project's `output/` |

`config/definitions.yaml` holds the study definitions and is identical at every site. Do not edit it
per site.

### Where outputs land

```
output/
├── intermediate_phi/<NN_step>/   patient-level working files; never shared, never committed
└── final_no_phi/<NN_step>/       aggregate, PHI-free outputs; the set to share
    └── logs/                     run logs, safe to share
```

Each numbered script writes only to its own `<NN_step>/` subfolder in each tree.

## Prerequisites

- Python 3.10+ and R 4.x with `jsonlite` (`arrow` too, once `04_descriptive` reads the analytic dataset)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip install -r requirements.txt
```

## Running the pipeline

macOS / Linux:

```bash
./run_pipeline.sh
```

Windows (PowerShell):

```powershell
.\run_pipeline.ps1
```

### Testing on synthetic data

`code/dev/make_synthetic.py` writes hand-built CLIF 3.0 fixtures to `dev_data/`, one patient per edge
case. The test runs the pipeline on those fixtures and checks every result against the known answer.

```bash
.venv/bin/python tests/test_01_cohort.py           # Windows: .venv\Scripts\python tests\test_01_cohort.py
```

## Pipeline steps

| Step | Language | Description |
|---|---|---|
| `01_cohort` | Python | Index CRRT episode, t0, phosphate and 28-day outcome windows, pre-CRRT hypophosphatemia exclusion, CONSORT counts |
| `02_covariates` | Python | *Stub.* Baseline characteristics and illness severity in the 24 h before t0 |
| `03_outcomes` | Python | *Stub.* Hypophosphatemia, phosphate repletion, respiratory and hospital outcomes |
| `04_descriptive` | R | *Stub.* Descriptive tables and models from the analytic dataset |

## Project structure

```
clif-epi-hypophosphatemia/
├── README.md
├── requirements.txt
├── run_pipeline.sh / run_pipeline.ps1
├── config/
│   ├── config.example.json
│   └── definitions.yaml           shared study definitions, pinned CLIF 3.0 ref
├── code/
│   ├── utils.py / utils.R
│   ├── clif_load.py               DuckDB views over CLIF tables
│   ├── 01_cohort.py
│   ├── 02_covariates.py
│   ├── 03_outcomes.py
│   ├── 04_descriptive.R
│   └── dev/make_synthetic.py      synthetic CLIF 3.0 fixtures
├── tests/
│   └── test_01_cohort.py
├── docs/                          planning notes and guides; local only, gitignored
├── references/                    literature PDFs; local only, gitignored
└── output/
    ├── intermediate_phi/
    └── final_no_phi/
```

## Data safety

Patient-level files stay in `output/intermediate_phi/`, which git ignores. A pre-push hook blocks
any push containing an `intermediate_phi` file, a data file outside `output/final_no_phi/`, or a
count below `small_cell_threshold`. `dev_data/` holds only synthetic data and is also ignored.
