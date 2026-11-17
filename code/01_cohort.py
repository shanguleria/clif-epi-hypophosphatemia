"""Cohort: adults whose first qualifying CRRT started in the ICU; one row per patient.

t0 = first qualifying CRRT record of the index episode. The outcome window runs from t0 to
CRRT end + window_after_crrt_end_hours, cut at ICU-stay end and hospital discharge.
"""
import json
from pathlib import Path

from clif_load import _quote, connect, hours
from utils import Definitions, check_version, load_config, provenance, step_dirs, suppress, write_step_log

STEP = Path(__file__).stem

cfg = load_config()
defs = Definitions()
check_version(cfg, defs)
phi_dir, share_dir, log_dir = step_dirs(__file__, cfg)
con = connect(cfg, defs, ["hospitalization", "adt", "renal_replacement_therapy", "labs"])

c = defs("cohort")
p = defs("phosphate")
modes = ", ".join(_quote(m) for m in c["crrt_modes"])

con.execute(f"""
CREATE TEMP TABLE adult AS
SELECT * FROM hospitalization WHERE age_at_admission >= {int(c['min_age_years'])}
""")

con.execute(f"""
CREATE TEMP TABLE icu_stay AS
WITH r AS (
  SELECT a.hospitalization_id, a.in_dttm, a.out_dttm,
         max(a.out_dttm) OVER (PARTITION BY a.hospitalization_id ORDER BY a.in_dttm, a.out_dttm
                               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prev_out
  FROM adt a JOIN adult USING (hospitalization_id)
  WHERE a.location_category = {_quote(c['icu_location_category'])}
), s AS (
  SELECT *, sum(CASE WHEN prev_out IS NULL OR in_dttm > prev_out + {hours(c['icu_merge_gap_hours'])}
                     THEN 1 ELSE 0 END)
            OVER (PARTITION BY hospitalization_id ORDER BY in_dttm, out_dttm ROWS UNBOUNDED PRECEDING) AS icu_stay_seq
  FROM r
)
SELECT hospitalization_id, icu_stay_seq, min(in_dttm) AS icu_in, max(out_dttm) AS icu_out
FROM s GROUP BY ALL
""")

con.execute(f"""
CREATE TEMP TABLE crrt_episode AS
WITH r AS (
  SELECT hospitalization_id, recorded_dttm,
         lag(recorded_dttm) OVER (PARTITION BY hospitalization_id ORDER BY recorded_dttm) AS prev
  FROM renal_replacement_therapy JOIN adult USING (hospitalization_id)
  WHERE mode_category IN ({modes})
), e AS (
  SELECT *, sum(CASE WHEN prev IS NULL OR recorded_dttm - prev >= {hours(c['crrt_episode_gap_hours'])}
                     THEN 1 ELSE 0 END)
            OVER (PARTITION BY hospitalization_id ORDER BY recorded_dttm ROWS UNBOUNDED PRECEDING) AS episode_seq
  FROM r
)
SELECT hospitalization_id, episode_seq, min(recorded_dttm) AS crrt_start, max(recorded_dttm) AS crrt_end
FROM e GROUP BY ALL
""")

# Ties on crrt_start break on hospitalization_id so the index is deterministic.
con.execute(f"""
CREATE TEMP TABLE indexed AS
SELECT h.patient_id, e.hospitalization_id, i.icu_stay_seq, i.icu_in, i.icu_out,
       e.crrt_start AS t0, e.crrt_end, h.admission_dttm, h.discharge_dttm, h.discharge_category,
       least(e.crrt_end + {hours(c['window_after_crrt_end_hours'])}, i.icu_out, h.discharge_dttm) AS window_end
FROM crrt_episode e
JOIN icu_stay i ON i.hospitalization_id = e.hospitalization_id
               AND e.crrt_start >= i.icu_in AND e.crrt_start <= i.icu_out
JOIN adult h ON h.hospitalization_id = e.hospitalization_id
QUALIFY row_number() OVER (PARTITION BY h.patient_id ORDER BY e.crrt_start, e.hospitalization_id) = 1
""")

con.execute(f"""
CREATE TEMP TABLE pre_phos AS
SELECT x.patient_id,
       count(l.lab_value_numeric) AS n_pre,
       count(*) FILTER (WHERE l.lab_value_numeric < {float(p['hypophosphatemia_below_mg_dl'])}) AS n_pre_low
FROM indexed x
JOIN labs l ON l.hospitalization_id = x.hospitalization_id
           AND l.lab_collect_dttm < x.t0
WHERE l.lab_category = {_quote(p['lab_category'])}
  AND l.lab_specimen_category = {_quote(p['specimen_category'])}
GROUP BY x.patient_id
""")

con.execute("""
CREATE TEMP TABLE cohort AS
SELECT x.*, coalesce(pp.n_pre, 0) > 0 AS has_baseline_phosphate
FROM indexed x LEFT JOIN pre_phos pp USING (patient_id)
WHERE coalesce(pp.n_pre_low, 0) = 0
ORDER BY x.patient_id
""")

out = phi_dir / "cohort.parquet"
con.execute(f"COPY cohort TO {_quote(out)} (FORMAT parquet)")


def n(sql):
    return con.execute(sql).fetchone()[0]


counts = [
    ("hospitalizations", n("SELECT count(*) FROM hospitalization")),
    ("adult_hospitalizations", n("SELECT count(*) FROM adult")),
    ("adult_hospitalizations_crrt_started_in_icu",
     n("SELECT count(DISTINCT e.hospitalization_id) FROM crrt_episode e JOIN icu_stay i "
       "ON i.hospitalization_id = e.hospitalization_id AND e.crrt_start BETWEEN i.icu_in AND i.icu_out")),
    ("patients_index_hospitalization", n("SELECT count(*) FROM indexed")),
    ("excluded_hypophosphatemia_before_crrt", n("SELECT count(*) FROM indexed") - n("SELECT count(*) FROM cohort")),
    ("cohort_patients", n("SELECT count(*) FROM cohort")),
    ("cohort_without_baseline_phosphate", n("SELECT count(*) FROM cohort WHERE NOT has_baseline_phosphate")),
]
thr = int(cfg["small_cell_threshold"])
(share_dir / "consort.csv").write_text(
    "step,n\n" + "".join(f"{k},{suppress(v, thr)}\n" for k, v in counts))
(share_dir / "provenance.json").write_text(json.dumps(provenance(cfg, defs), indent=2) + "\n")

dtypes = con.execute("SELECT column_name, column_type FROM (DESCRIBE cohort)").fetchall()
write_step_log(log_dir, STEP, [
    f"{STEP} ok",
    *(f"count {k} = {suppress(v, thr)}" for k, v in counts),
    *(f"column {col}: {typ}" for col, typ in dtypes),
    f"effective cohort definitions: {json.dumps(c)}",
    f"effective phosphate definitions: {json.dumps(p)}",
], defs)
print(f"{STEP}: wrote {out.name} and {share_dir.name}/consort.csv")
