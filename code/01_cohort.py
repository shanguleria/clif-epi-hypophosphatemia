"""Cohort: one row per adult patient, indexed at their first CRRT started in the ICU.

1. adult         hospitalizations with age >= min_age_years
2. icu_stay      ICU adt rows merged into stays across short or procedure-only gaps
3. crrt_episode  qualifying-mode CRRT records, split into episodes at long gaps
4. crrt_in_icu   episodes whose first record falls inside an ICU stay
5. index_crrt    each patient's earliest such episode; t0 = its first record; outcome windows
6. cohort        drop patients with low phosphate in the lookback before t0; flag those with none
"""
from datetime import timedelta

from utils import Step

step = Step(__file__, tables=["hospitalization", "adt", "renal_replacement_therapy", "labs"])
cohort = step.defs("cohort")
phosphate = step.defs("phosphate")

step.table("adult", """
    SELECT * FROM hospitalization WHERE age_at_admission >= $min_age
""", min_age=cohort["min_age_years"])

# Steps 2 and 3 use the same gaps-and-islands pattern: a row starts a new stay/episode when the
# gap since the previous one is too long, and a running count of those starts numbers them.
step.table("icu_stay", """
    WITH adult_adt AS (
        SELECT * FROM adt WHERE hospitalization_id IN (SELECT hospitalization_id FROM adult)
    ), icu_rows AS (
        SELECT hospitalization_id, in_dttm, out_dttm,
               max(out_dttm) OVER (PARTITION BY hospitalization_id ORDER BY in_dttm, out_dttm
                                   ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prev_out
        FROM adult_adt
        WHERE location_category = $icu
    ), gap_locations AS (
        SELECT r.hospitalization_id, r.in_dttm,
               bool_and(list_contains($bridge::VARCHAR[], a.location_category)) AS bridge_only
        FROM icu_rows r
        JOIN adult_adt a ON a.hospitalization_id = r.hospitalization_id
                        AND a.in_dttm < r.in_dttm AND a.out_dttm > r.prev_out
                        AND a.location_category <> $icu
        GROUP BY r.hospitalization_id, r.in_dttm
    ), numbered AS (
        SELECT r.*, count_if(r.prev_out IS NULL
                             OR (r.in_dttm > r.prev_out + $gap::INTERVAL AND NOT coalesce(g.bridge_only, false)))
                        OVER (PARTITION BY r.hospitalization_id ORDER BY r.in_dttm, r.out_dttm
                              ROWS UNBOUNDED PRECEDING) AS icu_stay_seq
        FROM icu_rows r
        LEFT JOIN gap_locations g USING (hospitalization_id, in_dttm)
    )
    SELECT hospitalization_id, icu_stay_seq, min(in_dttm) AS icu_in, max(out_dttm) AS icu_out
    FROM numbered
    GROUP BY hospitalization_id, icu_stay_seq
""", icu=cohort["icu_location_category"], gap=timedelta(hours=cohort["icu_merge_gap_hours"]),
     bridge=cohort["icu_bridge_location_categories"])

step.table("crrt_episode", """
    WITH crrt_rows AS (
        SELECT hospitalization_id, recorded_dttm,
               lag(recorded_dttm) OVER (PARTITION BY hospitalization_id ORDER BY recorded_dttm) AS prev_dttm
        FROM renal_replacement_therapy
        WHERE list_contains($modes::VARCHAR[], mode_category)
          AND hospitalization_id IN (SELECT hospitalization_id FROM adult)
    ), numbered AS (
        SELECT *, count_if(prev_dttm IS NULL OR recorded_dttm - prev_dttm >= $gap::INTERVAL)
                      OVER (PARTITION BY hospitalization_id ORDER BY recorded_dttm
                            ROWS UNBOUNDED PRECEDING) AS episode_seq
        FROM crrt_rows
    )
    SELECT hospitalization_id, episode_seq, min(recorded_dttm) AS crrt_start, max(recorded_dttm) AS crrt_end
    FROM numbered
    GROUP BY hospitalization_id, episode_seq
""", modes=cohort["crrt_modes"], gap=timedelta(hours=cohort["crrt_episode_gap_hours"]))

step.table("crrt_in_icu", """
    SELECT e.*, s.icu_stay_seq, s.icu_in, s.icu_out
    FROM crrt_episode e
    JOIN icu_stay s ON s.hospitalization_id = e.hospitalization_id
                   AND e.crrt_start BETWEEN s.icu_in AND s.icu_out
""")

# Ties on crrt_start break on hospitalization_id so the index is deterministic.
step.table("index_crrt", """
    SELECT h.patient_id, e.hospitalization_id, e.icu_stay_seq, e.icu_in, e.icu_out,
           e.crrt_start AS t0, e.crrt_end,
           least(e.crrt_end + $phosphate_window::INTERVAL, e.icu_out, h.discharge_dttm) AS phosphate_window_end,
           least(e.crrt_start + $followup::INTERVAL, h.discharge_dttm) AS followup_end,
           h.admission_dttm, h.discharge_dttm, h.discharge_category
    FROM crrt_in_icu e
    JOIN adult h ON h.hospitalization_id = e.hospitalization_id
    QUALIFY row_number() OVER (PARTITION BY h.patient_id ORDER BY e.crrt_start, e.hospitalization_id) = 1
""", phosphate_window=timedelta(hours=cohort["phosphate_window_after_crrt_end_hours"]),
     followup=timedelta(days=cohort["followup_days"]))

step.table("cohort", """
    WITH phosphate_before_t0 AS (
        SELECT i.patient_id,
               count(l.lab_value_numeric) AS n_measured,
               count_if(l.lab_value_numeric < $low) AS n_low
        FROM index_crrt i
        JOIN labs l ON l.hospitalization_id = i.hospitalization_id
                   AND l.lab_collect_dttm >= i.t0 - $lookback::INTERVAL AND l.lab_collect_dttm < i.t0
        WHERE l.lab_category = $lab AND l.lab_specimen_category = $specimen
        GROUP BY i.patient_id
    )
    SELECT i.*, coalesce(p.n_measured, 0) > 0 AS has_baseline_phosphate
    FROM index_crrt i
    LEFT JOIN phosphate_before_t0 p ON p.patient_id = i.patient_id
    WHERE coalesce(p.n_low, 0) = 0
    ORDER BY i.patient_id
""", low=phosphate["hypophosphatemia_below_mg_dl"], lab=phosphate["lab_category"],
     specimen=phosphate["specimen_category"], lookback=timedelta(hours=phosphate["lookback_before_t0_hours"]))

n_indexed, n_cohort = step.count("index_crrt"), step.count("cohort")
step.finish("cohort", counts={
    "hospitalizations": step.count("hospitalization"),
    "adult_hospitalizations": step.count("adult"),
    "adult_hospitalizations_crrt_started_in_icu": step.count("(SELECT DISTINCT hospitalization_id FROM crrt_in_icu)"),
    "patients_index_hospitalization": n_indexed,
    "excluded_hypophosphatemia_before_crrt": n_indexed - n_cohort,
    "cohort_patients": n_cohort,
    "cohort_without_baseline_phosphate": step.count("cohort WHERE NOT has_baseline_phosphate"),
})
