"""Runs 01_cohort on the synthetic sandbox and checks it against the planted ground truth.

    .venv/bin/python tests/test_01_cohort.py
"""
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "code"), str(ROOT / "code" / "dev")]
import make_synthetic as syn  # noqa: E402
from utils import Definitions  # noqa: E402

DEV_CFG = ROOT / "dev_data" / "config.dev.json"
OUT = ROOT / "dev_data" / "output"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else f'  -> {detail}'}")


def run_step(script, cfg_path):
    env = {**os.environ, "CLIF_CONFIG": str(cfg_path)}
    return subprocess.run([sys.executable, str(ROOT / "code" / script)], env=env, capture_output=True, text=True)


syn.main()
r = run_step("01_cohort.py", DEV_CFG)
check("01_cohort exits 0", r.returncode == 0, r.stderr[-2000:])
if r.returncode:
    sys.exit(1)

con = duckdb.connect()
con.execute("SET TimeZone = 'UTC'")
rows = con.execute(f"SELECT * FROM read_parquet('{OUT / 'intermediate_phi/01_cohort/cohort.parquet'}')").fetchall()
cols = [d[0] for d in con.description]
got = {row[cols.index("patient_id")]: dict(zip(cols, row)) for row in rows}

check("cohort patients match", set(got) == set(syn.EXPECTED["cohort"]),
      f"extra {set(got) - set(syn.EXPECTED['cohort'])}, missing {set(syn.EXPECTED['cohort']) - set(got)}")
for pid, (hid, t0, end, wend, icu_in, base) in syn.EXPECTED["cohort"].items():
    g = got.get(pid)
    if g is None:
        continue
    exp = {"hospitalization_id": hid, "t0": syn.t(t0), "crrt_end": syn.t(end), "window_end": syn.t(wend),
           "icu_in": syn.t(icu_in), "has_baseline_phosphate": base}
    bad = {k: (g[k], v) for k, v in exp.items() if g[k] != v}
    check(f"{pid} index, window and baseline", not bad, bad)

with open(OUT / "final_no_phi/01_cohort/consort.csv") as f:
    consort = {row["step"]: row["n"] for row in csv.DictReader(f)}
thr = 11
for step, n in syn.EXPECTED["counts"].items():
    want = f"<{thr}" if 0 < n < thr else str(n)
    note = f" (true {n}, suppressed)" if want != str(n) else ""
    check(f"consort {step} = {want}{note}", consort.get(step) == want, consort.get(step))

prov = json.loads((OUT / "final_no_phi/01_cohort/provenance.json").read_text())
check("provenance block complete",
      {"site_id", "code_version", "clif_version", "clif_spec_ref", "definition_version", "generated"} <= set(prov), prov)

used = set()
for f in (OUT / "final_no_phi/logs").glob("*.defs_used.json"):
    used |= set(json.loads(f.read_text()))
unread = Definitions().all_keys() - used
check("every definitions.yaml key is read by a step", not unread, sorted(unread))

# Same tables with naive local timestamps (as CSV-era sites ship them) must give the same cohort.
naive = ROOT / "dev_data" / "clif_naive"
naive.mkdir(exist_ok=True)
for p in (ROOT / "dev_data" / "clif").glob("*.parquet"):
    con.execute(f"""COPY (SELECT * REPLACE ({', '.join(
        f"timezone('US/Central', {c}) AS {c}" for c, ty in con.execute(f"SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM read_parquet('{p}'))").fetchall()
        if ty.startswith('TIMESTAMP WITH'))}) FROM read_parquet('{p}')) TO '{naive / p.name}' (FORMAT parquet)""")
naive_cfg = ROOT / "dev_data" / "config.naive.json"
naive_cfg.write_text(json.dumps({**json.loads(DEV_CFG.read_text()), "data_directory": str(naive),
                                 "output_root": "output_naive"}))
r = run_step("01_cohort.py", naive_cfg)
check("naive-timestamp run exits 0", r.returncode == 0, r.stderr[-2000:])
if r.returncode == 0:
    t0s = dict(con.execute(f"SELECT patient_id, t0 FROM read_parquet('{ROOT / 'dev_data/output_naive/intermediate_phi/01_cohort/cohort.parquet'}')").fetchall())
    check("naive local timestamps localize to the same UTC instants", t0s == {k: v["t0"] for k, v in got.items()},
          {k: (t0s.get(k), v["t0"]) for k, v in got.items() if t0s.get(k) != v["t0"]})

v2 = ROOT / "dev_data" / "config.v2.json"
v2.write_text(json.dumps({**json.loads(DEV_CFG.read_text()), "clif_version": "2.1.0"}))
r = run_step("01_cohort.py", v2)
check("refuses a CLIF 2.x config", r.returncode != 0 and "refusing" in (r.stdout + r.stderr), r.stdout + r.stderr)

print(f"\n{sum(results)} passed, {len(results) - sum(results)} failed")
sys.exit(0 if all(results) else 1)
