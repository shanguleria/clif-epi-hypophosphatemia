"""Hand-built CLIF 3.0 fixtures in dev_data/, one patient per edge case. No real data involved.

    .venv/bin/python code/dev/make_synthetic.py

EXPECTED is the ground truth tests/test_01_cohort.py checks the pipeline against.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "dev_data"
T = datetime(2025, 1, 1, tzinfo=timezone.utc)


def t(h):
    return T + timedelta(hours=h)


hosp, adt, rrt, labs = [], [], [], []


def add_hosp(pid, hid, age, admit=0, icu=((2, 300, "icu"),), disch=400):
    hosp.append(dict(patient_id=pid, hospitalization_id=hid, admission_dttm=t(admit),
                     discharge_dttm=t(disch), age_at_admission=age, discharge_category="home"))
    adt.append(dict(hospitalization_id=hid, in_dttm=t(admit), out_dttm=t(icu[0][0]), location_category="ed"))
    for start, end, loc in icu:
        adt.append(dict(hospitalization_id=hid, in_dttm=t(start), out_dttm=t(end), location_category=loc))


def add_rrt(hid, start, end, mode):
    for h in range(start, end + 1):
        rrt.append(dict(hospitalization_id=hid, recorded_dttm=t(h), mode_category=mode, blood_flow_rate=200.0))


def add_phos(hid, at, value, specimen="plasma_blood"):
    labs.append(dict(hospitalization_id=hid, lab_category="phosphate", lab_value_numeric=value,
                     lab_collect_dttm=t(at), lab_result_dttm=t(at + 1), lab_specimen_category=specimen))


# p01 typical, long admission: included, baseline present, follow-up cut at t0 + 28 d
add_hosp("p01", "h01", 60, disch=1000); add_rrt("h01", 10, 60, "cvvhdf"); add_phos("h01", 5, 3.5)
# p02 age 17: not adult
add_hosp("p02", "h02", 17); add_rrt("h02", 10, 20, "cvvh")
# p03 age exactly 18, no phosphate ever: included without baseline
add_hosp("p03", "h03", 18); add_rrt("h03", 10, 20, "cvvhd")
# p04 phosphate 2.2 before CRRT: excluded
add_hosp("p04", "h04", 50); add_rrt("h04", 10, 20, "cvvh"); add_phos("h04", 5, 2.2)
# p05 scuf first, cvvhdf later: index at the cvvhdf start
add_hosp("p05", "h05", 55); add_rrt("h05", 10, 20, "scuf"); add_rrt("h05", 50, 70, "cvvhdf"); add_phos("h05", 5, 3.0)
# p06 ihd only: never qualifies
add_hosp("p06", "h06", 70); add_rrt("h06", 10, 14, "ihd")
# p07 two hospitalizations with CRRT: only the first is the index
add_hosp("p07", "h07a", 45); add_rrt("h07a", 10, 20, "cvvh"); add_phos("h07a", 5, 3.0)
add_hosp("p07", "h07b", 45, admit=1000, icu=((1002, 1300, "icu"),), disch=1400); add_rrt("h07b", 1010, 1020, "cvvh")
# p08 CRRT starts on the ward before ICU admission: never qualifies
add_hosp("p08", "h08", 65, icu=((100, 300, "icu"),)); add_rrt("h08", 50, 60, "cvvh")
# p09 30 h gap splits CRRT: index episode ends before the gap
add_hosp("p09", "h09", 40); add_rrt("h09", 10, 20, "cvvh"); add_rrt("h09", 50, 60, "cvvh"); add_phos("h09", 5, 3.0)
# p10 contiguous ICU-to-ICU transfer merges into one stay; phosphate window cut at ICU discharge
add_hosp("p10", "h10", 72, icu=((2, 100, "icu"), (100, 120, "icu"), (120, 400, "ward")))
add_rrt("h10", 105, 118, "cvvhdf"); add_phos("h10", 100, 3.0)
# p11 low phosphate only in urine, at exactly t0, or after t0: not excluded, and no pre-t0 baseline
add_hosp("p11", "h11", 33); add_rrt("h11", 10, 20, "cvvh")
add_phos("h11", 5, 2.0, specimen="urine"); add_phos("h11", 10, 2.4); add_phos("h11", 15, 1.9)
# p12 10 h in the OR then radiology between ICU rows: bridged, one stay from hour 2
add_hosp("p12", "h12", 61, icu=((2, 50, "icu"), (50, 55, "procedural"), (55, 60, "radiology"), (60, 300, "icu")))
add_rrt("h12", 70, 80, "cvvh"); add_phos("h12", 65, 3.0)
# p13 4 h on the ward between ICU rows: within the 6 h gap, one stay from hour 2
add_hosp("p13", "h13", 62, icu=((2, 50, "icu"), (50, 54, "ward"), (54, 300, "icu")))
add_rrt("h13", 70, 80, "cvvh"); add_phos("h13", 65, 3.0)
# p14 OR then ward, 20 h out of the ICU: a new stay from hour 70
add_hosp("p14", "h14", 63, icu=((2, 50, "icu"), (50, 55, "procedural"), (55, 70, "ward"), (70, 300, "icu")))
add_rrt("h14", 80, 90, "cvvh"); add_phos("h14", 75, 3.0)
# p15 low phosphate 95 h before t0, outside the 72 h lookback: kept, no baseline
add_hosp("p15", "h15", 58); add_rrt("h15", 100, 110, "cvvh"); add_phos("h15", 5, 2.0)
# p16 avvh only: in the with_avvh cohort only
add_hosp("p16", "h16", 47); add_rrt("h16", 10, 20, "avvh"); add_phos("h16", 5, 3.0)
# p17 avvh, then cvvhdf after a 30 h gap: primary indexes at the cvvhdf start, with_avvh at the avvh start
add_hosp("p17", "h17", 52); add_rrt("h17", 10, 20, "avvh"); add_rrt("h17", 50, 60, "cvvhdf"); add_phos("h17", 5, 3.0)

# patient_id: (hospitalization_id, t0 h, crrt_end h, phosphate_window_end h, followup_end h,
#              icu_in h, has_baseline)
PRIMARY = {
    "p01": ("h01", 10, 60, 108, 682, 2, True),
    "p03": ("h03", 10, 20, 68, 400, 2, False),
    "p05": ("h05", 50, 70, 118, 400, 2, True),
    "p07": ("h07a", 10, 20, 68, 400, 2, True),
    "p09": ("h09", 10, 20, 68, 400, 2, True),
    "p10": ("h10", 105, 118, 120, 400, 2, True),
    "p11": ("h11", 10, 20, 68, 400, 2, False),
    "p12": ("h12", 70, 80, 128, 400, 2, True),
    "p13": ("h13", 70, 80, 128, 400, 2, True),
    "p14": ("h14", 80, 90, 138, 400, 70, True),
    "p15": ("h15", 100, 110, 158, 400, 2, False),
    "p17": ("h17", 50, 60, 108, 400, 2, True),
}

EXPECTED = {
    "counts": {
        "hospitalizations": 18,
        "adult_hospitalizations": 17,
        "primary.adult_hospitalizations_crrt_started_in_icu": 14,
        "primary.patients_index_hospitalization": 13,
        "primary.excluded_hypophosphatemia_before_crrt": 1,
        "primary.cohort_patients": 12,
        "primary.cohort_without_baseline_phosphate": 3,
        "with_avvh.adult_hospitalizations_crrt_started_in_icu": 15,
        "with_avvh.patients_index_hospitalization": 14,
        "with_avvh.excluded_hypophosphatemia_before_crrt": 1,
        "with_avvh.cohort_patients": 13,
        "with_avvh.cohort_without_baseline_phosphate": 3,
    },
    "cohort": {
        "primary": PRIMARY,
        "with_avvh": {**PRIMARY,
                      "p16": ("h16", 10, 20, 68, 400, 2, True),
                      "p17": ("h17", 10, 20, 68, 400, 2, True)},
    },
}


def main():
    data = DEV / "clif"
    data.mkdir(parents=True, exist_ok=True)
    for name, rows in [("hospitalization", hosp), ("adt", adt), ("renal_replacement_therapy", rrt), ("labs", labs)]:
        pd.DataFrame(rows).to_parquet(data / f"clif_{name}.parquet", index=False)
    (DEV / "config.dev.json").write_text(json.dumps({
        "site": "SYNTHETIC", "data_directory": str(data), "filetype": "parquet", "timezone": "US/Central",
        "clif_version": "3.0.0", "small_cell_threshold": 11, "redact_site_names": [], "output_root": "output",
    }, indent=2) + "\n")
    print(f"wrote synthetic CLIF 3.0 tables to {data}")


if __name__ == "__main__":
    main()
