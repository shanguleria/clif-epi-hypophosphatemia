# CLIF 3.0 spec check: CRRT hypophosphatemia cohort

Retrieved 2026-11-16 from public GitHub, PyPI and clif-icu.com only. No local data was read.
Anything not confirmed against a cited source is marked **UNVERIFIED**.

## 0. Is CLIF 3.0 released?

**No. It is a draft that is still changing.**

| Evidence | Source |
|---|---|
| Tag `v3.0.0` exists, but the GitHub release is flagged **pre-release**. It was published 2026-03-09 with the body "Multimodal" | https://github.com/Common-Longitudinal-ICU-data-Format/CLIF/releases/tag/v3.0.0 (commit `34b4214f12146103a2de2a02537182c025282dd7`) |
| Branch `3.0` is **105 commits ahead** of the `v3.0.0` tag. Its head is `3ee2e0292d55017506d247deacc4edf5a1d0054d` (2026-11-16, "feat(mCIDE): add sufentanil, tirofiban and intermittent forms of continuous meds") | GitHub compare API `v3.0.0...3.0` |
| A 2026-09-15 commit on the med vocabularies is titled "PENDING 3.0 REFINALIZATION" | commit history of `mCIDE/medication_admin_intermittent/...med_categories.csv` on `3.0` |
| The dictionary page is titled "CLIF 3.0 Data Dictionary (**Future Release**)" and says "CLIF v3.0 — going multimodal. **Work in progress.**" | https://clif-icu.com/data-dictionary/data-dictionary-3.0.0 (page "Last Updated: November 16, 2026") |
| The latest non-prerelease is `v2.1.1` (2026-01-02). `v2.2.0` is marked OBSOLETE ("Upgrading to 3.0 multimodal instead") | CLIF releases page |

**The `v3.0.0` tag is not usable for this study.** At that tag the airway mCIDE (`mCIDE/airway/clif_airway_categories.csv`) returns 404. The table is still `crrt_therapy`. The intermittent med CSV has no phosphate rows. Everything below therefore refers to **branch `3.0` @ `3ee2e02`**. That is a moving target: re-pin the SHA before the analysis is frozen.

### Sources used (all at `3ee2e0292d55017506d247deacc4edf5a1d0054d` unless noted)

Base: `https://github.com/Common-Longitudinal-ICU-data-Format/CLIF/blob/3ee2e0292d55017506d247deacc4edf5a1d0054d/`

- Data dictionary (authoritative for table structure): https://clif-icu.com/data-dictionary/data-dictionary-3.0.0
- DDL: `ddl/3.0/CLIF3.0_MYSQL_ddl.sql`. **Stale for RRT** (see §1). No schema YAML or JSON lives in the CLIF repo. The YAML schemas are in clifpy (§9).
- mCIDE CSVs:
  - `mCIDE/renal_replacement_therapy/clif_renal_replacement_therapy_mode_categories.csv`
  - `mCIDE/labs/clif_lab_categories.csv` and `mCIDE/labs/README.md`
  - `mCIDE/medication_admin_intermittent/clif_medication_admin_intermittent_med_categories.csv`
  - `mCIDE/medication_admin_continuous/clif_medication_admin_continuous_med_categories.csv`
  - `mCIDE/medication_admin_{continuous,intermittent}/clif_medication_med_group_categories.csv`
  - `mCIDE/respiratory_support/clif_respiratory_support_device_categories.csv`
  - `mCIDE/airway/clif_airway_categories.csv`
  - `mCIDE/mcs/clif_mcs_{support,device,configuration,setting}_category.csv`
  - `mCIDE/adt/clif_adt_location_categories.csv`
  - `mCIDE/hospitalization/clif_hospitalization_discharge_categories.csv`
  - `mCIDE/patient/clif_patient_{sex,race}_categories.csv`
  - `mCIDE/vitals/clif_vitals_categories.csv`
  - `mCIDE/input/clif_input_{category,group}.csv`
  - `mCIDE/output/clif_output_categories.csv`
- 2.1.0 comparison: tag `v2.1.0`. Same paths, plus `ddl/2.1/CLIF2.1_MYSQL_ddl.sql` and `mCIDE/crrt_therapy/clif_crrt_therapy_mode_categories.csv`.

**General 2.1 → 3.0 change:** every `*_category`, `*_group` and `*_type` value is lowercase snake_case in 3.0. Examples: `IMV` → `imv`, `Expired` → `expired`, `Male` → `male`, `l&d` → `l_and_d`. The commit is "Standardize mCIDE category, type, and group values to lowercase snake_case" (2026-03-09). Lab `reference_unit` values are lowercase too (`mg/dL` → `mg/dl`, `mmHg` → `mmhg`). Code that string-matches 2.1 values will silently match nothing.

---

## 1. Renal replacement therapy

| Item | CLIF 3.0 (branch) | vs 2.1.0 | Status |
|---|---|---|---|
| Table | `renal_replacement_therapy` (maturity **Alpha**) | `crrt_therapy`. 3.0 merges `crrt_therapy` and `intermittent_dialysis` into one table (commit `c91fdff`, PR #224, 2026-06-30) | **renamed** |
| Timing | `recorded_dttm` only (long, one row per recorded parameter set). There is **no start/stop field** | same in 2.1 | ok. Start and end must be derived |
| Mode | `mode_name`, `mode_category` ∈ {`scuf`, `cvvh`, `cvvhd`, `cvvhdf`, `avvh`, `ihd`, `iuf`} | `crrt_mode_name` / `crrt_mode_category` ∈ {scuf, cvvh, cvvhd, cvvhdf, avvh}. `ihd` and `iuf` are new | **renamed** (columns) and expanded |
| Blood flow | `blood_flow_rate` FLOAT, mL/min, range 100–600 | same name. 2.1 range 150–350 | ok |
| Replacement | `pre_filter_replacement_fluid_rate`, `post_filter_replacement_fluid_rate` FLOAT, mL/hr. CRRT modes only | same | ok |
| Dialysate | `dialysate_flow_rate` FLOAT, mL/hr (IHD converted from mL/min ×60), range 0–70000 | same name, 0–10000 | ok |
| Net ultrafiltration | **Removed from this table.** It now lives in `output`: `output_category = ultrafiltration`, `output_group = ultrafiltration`, `output_value` in mL with `output_unit` = `mL`. The dictionary says it "should reflect net ultrafiltration only" | 2.1 `crrt_therapy.ultrafiltration_out` (mL/hr) | **moved** |
| Fluids delivered | `input` table, `input_group = renal_replacement_fluids` (category `renal_replacement_fluids`), `input_volume` in mL, free-text `input_name` | 2.1 `intake_output` | moved |
| Fluid composition | Only `potassium_bath` (INT, mEq/L, 0–4) and `calcium_bath` (FLOAT, mEq/L, 0–4) exist. The dictionary describes them as distinguishing `ihd` (populated) from `iuf` (null). It does not say whether they are populated for CRRT modes (**UNVERIFIED**) | not in 2.1 | **gap for phosphate**. There is no field for dialysate or replacement-fluid phosphate content |
| Other | `device_id`, `dialysis_machine_name` | `device_id` existed in 2.1 DDL | ok |

**Internal inconsistency on the 3.0 branch:** `ddl/3.0/CLIF3.0_MYSQL_ddl.sql` still defines `crrt_therapy` (with `crrt_mode_category` and `ultrafiltration_out`) and a separate `intermittent_dialysis`. The DDL links to a `mCIDE/crrt_therapy/` path that no longer exists on the branch. The dictionary, the README POC table and the mCIDE folder all use `renal_replacement_therapy`. I treat the dictionary as authoritative. Confirm with the table POCs.

**Effluent dose (mL/kg/h)** can be built from 3.0 fields:

    (dialysate_flow_rate + pre_filter_replacement_fluid_rate + post_filter_replacement_fluid_rate + net UF rate) / weight_kg

- Net UF has to be converted from `output` volume events (mL) to a rate, aligned in time to RRT rows. This is a derivation choice the 2.1 table did not require.
- Whether to correct for pre-filter dilution is a separate analytic choice.
- Weight comes from `vitals.weight_kg`.

**CRRT-only inclusion:** CRRT modes = `scuf`, `cvvh`, `cvvhd`, `cvvhdf`. `avvh` is "Accelerated Veno-Venous Hemofiltration also called ARRT or PIRRT", a prolonged-intermittent therapy, and needs a decision. `ihd` and `iuf` are excluded by TASK.md.

## 2. Labs (`labs`, Beta)

Columns: `lab_category`, `lab_value`, `lab_value_numeric`, `reference_unit`, `lab_collect_dttm`, `lab_result_dttm`, `lab_order_category`, `lab_specimen_category` ∈ {plasma_blood, pleural, peritoneal, urine, bal}.

| Analyte | `lab_category` | `reference_unit` (3.0) | 2.1.0 | Status |
|---|---|---|---|---|
| Phosphate | `phosphate` (order cat `misc`, specimen `plasma_blood`; note says "sometimes called 'phosphorus'") | `mg/dl` | `phosphate`, `mg/dL`, order cat `coags` | ok (unit case changed) |
| Creatinine | `creatinine` | `mg/dl` | `mg/dL` | ok. **In 3.0 the same category also covers urine, peritoneal and pleural creatinine.** Filter `lab_specimen_category == 'plasma_blood'` for KDIGO |
| Total bilirubin | `bilirubin_total` | `mg/dl` | `mg/dL` | ok |
| INR | `inr` | `(no units)` | same | ok |
| PaO2 | `po2_arterial` (distinct from `po2_mixed_venous`, `po2_ecmo_pre`, `po2_ecmo_post`) | `mmhg` | `mmHg` | ok |

TASK.md thresholds (< 2.5 and < 1.5 mg/dL) are in the CLIF reference unit for phosphate, so no conversion is needed.

## 3. Medications

**Phosphate repletion (3.0 branch).**
- `phosphate_repletion` is a `med_group` in both `clif_medication_med_group_categories.csv` files. Its description is "Phosphate salts for repletion; roll-up of salt-level categories".
- All four `med_category` values exist, **in `medication_admin_intermittent` only**, each with `med_group = phosphate_repletion` and standardized `med_dose_unit = mmol` (mmol phosphate):
  - `potassium_phosphate` (IV)
  - `potassium_sodium_phosphate` (oral)
  - `sodium_glycerophosphate` (IV)
  - `sodium_phosphate` (IV; the note says to exclude bowel prep and enemas)
- The continuous med CSV has no phosphate-salt rows.
- Columns used: `admin_dttm`, `med_category`, `med_group`, `med_dose`, `med_dose_unit`, `med_route_category`, and `mar_action_group` ∈ {administered, not_administered, other}.
- Status: **ok on branch, absent in 2.1.0 and absent at tag v3.0.0.** The salt split was added by the 2026-09-14 commit (CLIF issue #200: "split the repletion categories based on salts").
- TASK.md writes `medication_group`. The column is **`med_group`**.
- Continuously infused phosphate has no continuous category. Whether any site infuses it continuously is **UNVERIFIED**.

**TPN.**
- `med_category = tpn`, `med_group = fluids_electrolytes`, in both continuous (`ml/hr`) and intermittent (`ml`).
- Also in `input`: `input_category = parenteral_nutrition`, `input_group = nutrition`.
- There is no field for TPN phosphate content.
- Status: ok. In 2.1, `tpn` was in continuous only.

**Vasopressors for norepinephrine equivalents** (`medication_admin_continuous`, `med_group = vasoactive`). The 2.1 group was `vasoactives`, so this is a **rename**:

| med_category | CSV unit |
|---|---|
| `norepinephrine` | mcg/kg/min |
| `epinephrine` | mcg/kg/min |
| `phenylephrine` | mcg/kg/min |
| `dopamine` | mcg/kg/min |
| `vasopressin` | units/min |
| `angiotensin_ii` | ng/kg/min |

The DDL `med_dose_unit` text says units "are not standardized across drugs". The 3.0 continuous CSV carries a `med_dose_unit` column. Sites may therefore deliver other units, so convert before summing.

## 4. Respiratory support (`respiratory_support`, Beta)

- `device_category` ∈ {imv, nippv, cpap, hfnc, face_mask, trach_collar, t_piece, nasal_cannula, blow_by, room_air, other}. **IMV = `imv`** (2.1: `IMV`). Renamed by case.
- FiO2: `fio2_set` (fraction, e.g. 0.21). Unchanged.
- `tracheostomy` INT 0/1 is **still present** in 3.0.
- SpO2: `vitals.vital_category = spo2` (%). Unchanged.
- PaO2: `labs.po2_arterial`. S/F and P/F are therefore both derivable.

## 5. Airway / tracheostomy

- `airway` table exists on the 3.0 branch with maturity **Concept**. The dictionary defines that as "constructed at least partially at one site, but not yet used in a federated project".
- Columns: `airway_id`, `placed_dttm`, `removed_dttm`, `airway_category` ∈ {`ett`, `trach`, `npa`, `opa`}, `airway_size`, `is_cuffed`.
- Absent in 2.1.0 and at tag v3.0.0.
- The TASK.md definition (`ett` → `trach`) maps exactly to the fields.
- Concept maturity means availability across sites is **UNVERIFIED** and likely sparse. The fallback is `respiratory_support.tracheostomy` (0/1) and `device_category = trach_collar`.

## 6. ECMO

- `ecmo_mcs` (2.1, wide) became **`mcs`** (3.0, Alpha, long format: one setting per row). **Renamed.**
- ECMO = `support_category = 'ecmo'`. The other support values are lvad, rvad, iabp.
- `config_category` for ECMO ∈ {v_v, v_a, v_av, vv_a, v_pa_single, v_pa_dual, hybrid}.
- `setting_category` ∈ {rpm, flow, sweep, fdo2, p_ven, p_art, delta_pressure, power, pulsatility_index, performance, iabp_ratio}, with values in `setting_value`. `device_category` holds brand values (cardiohelp, rotaflow, centrimag, …).
- Minor documentation inconsistency: the configuration CSV descriptions say `mcs_category == ecmo`, but the column is `support_category`.

## 7. Diagnoses

- **`hospital_diagnosis`** (Beta):
  - Columns: `diagnosis_code`, `diagnosis_code_format` ∈ {`ICD10CM`, `ICD9CM`}, `diagnosis_primary` 0/1, and `poa_present` 0/1.
  - Rows with Unknown or Exempt POA are dropped at ETL; only 1 and 0 are allowed.
  - The table has **no timestamps**. These are finalized billing codes, and the dictionary says to use them "for comorbidity scores, not as input features".
  - Unchanged from 2.1.0.
- **`patient_diagnosis`** (Alpha):
  - Columns: `patient_id`, `hospitalization_id`, `diagnosis_code` (ICD-10-CM only), `diagnosis_code_format = ICD10CM`, `source_type` ∈ {problem_list, medical_history, encounter_dx}, `start_dttm`, `end_dttm`.
  - It offers a time-stamped route to prior-to-admission conditions.
- Prior-to-admission ESRD has two options:
  - (a) index-hospitalization `hospital_diagnosis` with `poa_present = 1`;
  - (b) `hospital_diagnosis` from **earlier** hospitalizations of the same `patient_id` (ordered by `hospitalization.admission_dttm`);
  - optionally (c) `patient_diagnosis` with `start_dttm` before admission.
- Code punctuation (dotted vs undotted) is not specified in the DDL or dictionary (**UNVERIFIED**). clifpy's `cci.yaml` lists undotted codes (e.g. `N18`, `Z992`).
- clifpy `calculate_cci` filters `diagnosis_code_format` to ICD10CM. It applies **no POA filter** (`clifpy/utils/comorbidity.py` @ v0.4.9).

## 8. ADT, hospitalization, patient, vitals

| Element | 3.0 field and values | vs 2.1.0 |
|---|---|---|
| ICU | `adt.location_category = icu`. Also `in_dttm`, `out_dttm`, `location_type` | same value (`l&d` → `l_and_d`); new `room_id`, `bed_id` |
| Age | `hospitalization.age_at_admission` INT, years | same |
| Discharge | `hospitalization.discharge_category` ∈ {home, snf, expired, acute_ip_rehab, hospice, ltach, acute_care_hosp, group_home, chemical_dependency, ama, assisted_living, still_admitted, missing, other, mental_health_hosp, shelter, jail} | renamed by case and abbreviation (`Expired` → `expired`, `Skilled Nursing Facility (SNF)` → `snf`, `Psychiatric Hospital` → `mental_health_hosp`) |
| Death/hospice | **`expired`** and **`hospice`**. There is no value named `death`. TASK.md's "death" must map to `expired` | renamed |
| Sex | `patient.sex_category` ∈ {male, female, unknown} | case |
| Race | `patient.race_category` ∈ {black_or_african_american, white, american_indian_or_alaska_native, asian, native_hawaiian_or_other_pacific_islander, middle_eastern_or_north_african, unknown, other} | case; `middle_eastern_or_north_african` is **new** in 3.0 |
| Ethnicity | `patient.ethnicity_category` ∈ {hispanic, non_hispanic, unknown} | case |
| Weight/height/MAP | `vitals.vital_category` = `weight_kg` (kg), `height_cm` (cm), `map` (mmHg). Also `recorded_dttm` and new optional `measured_dttm` | same names |

## 9. clifpy

- **PyPI latest: `clifpy 2.1.0`** (https://pypi.org/pypi/clifpy/json; GitHub release v2.1.0 2026-08-20). The versions jumped from 0.5.0 (2026-06-11) to 2.1.0, so clifpy and CLIF version numbers are independent.
- **Partial 3.0 support in clifpy 2.1.0 and `main`:**
  - It ships `clifpy/schemas/2.1/` and `clifpy/schemas/3.0/` plus `schemas/crosswalks/clif_2.1_to_3.0.yaml`.
  - `DEFAULT_CLIF_VERSION = "2.1"` (`clifpy/schemas/__init__.py`). 3.0 is opt-in via `clif_version="3.0"` or config `clif_version` (`clifpy/tables/base_table.py`).
- **But its 3.0 schemas lag the CLIF 3.0 branch.** They were last synced 2026-08-20 ("close structural drift between 3.0 schemas and upstream CLIF DDL"), which was before the med salt split.
  - They define `crrt_therapy` (with `crrt_mode_category` and `ultrafiltration_out`) and `intermittent_dialysis`. There is **no `renal_replacement_therapy` schema, even on `main`**.
  - `medication_admin_intermittent` (3.0 schema) has a single `med_category: phosphate_repletion` (group `other`, unit mmol). It does **not** have the four salt categories.
  - Table classes exist on `main` for `airway`, `mcs`, `input` and `output`. In the 2.1.0 release, the table classes are only the 2.1 set (schemas exist for 3.0 tables, but there is no `airway.py`, `mcs.py`, etc.).
- **Pinned `clifpy==0.4.9`** (this repo's `requirements.txt`) **does not support 3.0:**
  - It has a single flat `clifpy/schemas/` (2.1) with `crrt_therapy` and `ecmo_mcs`.
  - It has no table class or schema for `renal_replacement_therapy`, `airway`, `mcs`, `input` or `output`, and no version switch.
  - Its permissible values are 2.1 (`IMV`, `High Flow NC`, …). The 0.4.9 validator lowercases values (`clifpy/utils/validator.py` ~L125–132), so case-only renames like `imv` may pass. Renamed values such as `hfnc` would still be flagged. Exact behavior (warn vs fail) is **UNVERIFIED**.
  - Conclusion: 3.0 tables needed here cannot be loaded through 0.4.9's table API. They would have to be read as parquet directly (duckdb or pandas).
- Upgrading past 0.4.9 crosses the 0.5.0 timezone-handling change that motivated the pin, so it needs deliberate revalidation.

**Synthetic sandbox:**
- The clif-icu skill's `setup_dev_data.sh` pins `synthetic_clif` **v0.7.0** and states "the sandbox always emits 2.1 — 3.0 needs clifpy crosswalk" (`~/.claude/plugins/cache/clif-skills/clif-icu/a3c428196cdc/skills/clif-icu/scripts/setup_dev_data.sh`).
- `synthetic_clif` **v0.8.0** (2026-11-11) now emits 3.0 by default, including `airway`, `mcs`, `input` and `output`. However, it builds its schema "from the CLIF 3.0 branch as packaged in clifpy", and its README lists `intermittent_dialysis` as a new table. It therefore likely emits `crrt_therapy` rather than `renal_replacement_therapy` and lacks the phosphate salts (**UNVERIFIED**; not executed).

---

## Summary: TASK.md element → CLIF 3.0 source → status

| TASK.md element | CLIF 3.0 source (branch `3.0` @ `3ee2e02`) | Status |
|---|---|---|
| Age ≥18 | `hospitalization.age_at_admission` | ok |
| ICU admission / ICU stay / ICU LOS | `adt.location_category = 'icu'`, `in_dttm`/`out_dttm` | ok |
| CRRT start/end | `renal_replacement_therapy.recorded_dttm`, `mode_category` (derive first/last; 24 h gap rule) | renamed (`crrt_therapy` → `renal_replacement_therapy`; `crrt_mode_category` → `mode_category`) |
| CRRT only, not other RRT | `mode_category` ∈ {scuf, cvvh, cvvhd, cvvhdf}; exclude ihd, iuf; `avvh` TBD | renamed and expanded |
| CRRT modality | `mode_category` | renamed |
| CRRT dose | RRT rates + `output` (`output_category = ultrafiltration`) + `vitals.weight_kg` | renamed / moved (net UF left the RRT table) |
| Phosphate-containing dialysate | none (only `potassium_bath`, `calcium_bath`) | **gap** |
| Baseline / outcome phosphate | `labs.lab_category = 'phosphate'`, `mg/dl` | ok (unit lowercased) |
| Phosphate repletion | `medication_admin_intermittent`, `med_group = 'phosphate_repletion'`, 4 salt categories, `mmol` | ok on branch only (absent in 2.1.0, v3.0.0 tag, clifpy) |
| TPN | `med_category = 'tpn'` (cont./interm.); `input.input_category = 'parenteral_nutrition'` | ok |
| BMI | `vitals` `weight_kg`, `height_cm` | ok |
| Sex / race | `patient.sex_category`, `race_category` | renamed (case) |
| ESRD prior to admission | `hospital_diagnosis` (`poa_present`, prior hospitalizations) / `patient_diagnosis` | ok, but needs a definition |
| Charlson | `hospital_diagnosis` (clifpy `calculate_cci`) | ok (POA handling is a decision) |
| IMV status / extubation / VFD-28 | `respiratory_support.device_category = 'imv'` | renamed (case) |
| P/F, S/F | `labs.po2_arterial`; `vitals.spo2`; `respiratory_support.fio2_set` | ok |
| MAP | `vitals.vital_category = 'map'` | ok |
| NE equivalents | `medication_admin_continuous`, `med_group = 'vasoactive'` | renamed (`vasoactives` → `vasoactive`) |
| ECMO status | `mcs.support_category = 'ecmo'` | renamed (`ecmo_mcs` → `mcs`, long format) |
| KDIGO AKI | `labs.creatinine` filtered to `lab_specimen_category = 'plasma_blood'` | ok (new specimen pitfall) |
| Total bilirubin, INR | `bilirubin_total`, `inr` | ok |
| Tracheostomy time | `airway.airway_category` `ett` → `trach`, `placed_dttm` | ok on branch; Concept maturity |
| In-hospital mortality | `discharge_category` ∈ {`expired`, `hospice`} | renamed (no `death` value) |
| Discharge category | `hospitalization.discharge_category` | renamed (case/abbrev) |
| Tooling | clifpy 0.4.9 pinned | **gap** (no 3.0 support) |

## Gaps needing a researcher decision

1. **Which 3.0 ref?** 3.0 is unreleased (pre-release tag, "Future Release" dictionary). The `v3.0.0` tag lacks airway, the RRT rename and the phosphate salts. Pin a branch SHA now and re-check before freezing, or wait for a final tag.
2. **Phosphate-containing dialysate/replacement fluid is not representable.** Options:
   - drop the covariate;
   - parse free-text `input.input_name` for `input_group = renal_replacement_fluids` (site-specific, non-standard);
   - collect a site-level fluid-formulary questionnaire;
   - propose a `phosphate_bath`-type field to the RRT POCs.
3. **RRT table naming conflict.** The DDL says `crrt_therapy` and `intermittent_dialysis`; the dictionary and mCIDE say `renal_replacement_therapy`. clifpy and synthetic_clif follow the DDL. Decide which name the pipeline reads, or support both.
4. **`avvh` (PIRRT/ARRT)**: count it as CRRT or exclude it.
5. **Effluent dose derivation.** Net UF now lives in `output` as volumes, not rates. Define the time alignment and rate conversion, and whether to apply a pre-filter dilution correction.
6. **ESRD definition**: POA=1 at index vs prior-encounter codes vs `patient_diagnosis`, and the ICD code list. Also decide whether Charlson is restricted to POA=1 (clifpy's `calculate_cci` does not filter POA).
7. **Tracheostomy**: `airway` is Concept maturity and likely sparse. Decide the fallback to `respiratory_support.tracheostomy` / `trach_collar`.
8. **TASK.md wording fixes**: `medication_group` → `med_group`; mortality "death" → `expired`.
9. **clifpy pin**: 0.4.9 cannot load the 3.0 RRT, airway or mcs tables. clifpy 2.1.0 has a 3.0 schema, but it is stale (no `renal_replacement_therapy`, no phosphate salts) and crosses the 0.5.0 tz change. Choose between direct parquet reads under the 0.4.9 pin and a validated upgrade.
10. **Synthetic test data**: the skill's sandbox emits 2.1 (synthetic_clif v0.7.0). v0.8.0 emits 3.0, but likely under the clifpy-packaged schema (UNVERIFIED). Test fixtures for `renal_replacement_therapy` and the phosphate salt categories may need to be hand-built.
11. **Phosphate given by continuous infusion** has no continuous `med_category` (UNVERIFIED whether any site does this).
