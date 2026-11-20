import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from clif_load import connect

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "config.json"
DEFINITIONS = ROOT / "config" / "definitions.yaml"
REQUIRED = ("site", "data_directory", "filetype", "timezone", "clif_version",
            "small_cell_threshold")


def load_config():
    # CLIF_CONFIG points the pipeline at the synthetic sandbox; real runs leave it unset.
    path = Path(os.environ.get("CLIF_CONFIG", CONFIG))
    if not path.is_file():
        raise FileNotFoundError(f"{path} missing: copy config/config.example.json and edit it")
    cfg = json.loads(path.read_text())
    missing = [k for k in REQUIRED if k not in cfg]
    if missing:
        raise KeyError(f"{path} lacks required keys: {missing}")
    cfg["output_root"] = str((path.parent / cfg["output_root"]).resolve()
                             if "output_root" in cfg else ROOT / "output")
    return cfg


def _leaves(node, prefix):
    if isinstance(node, dict):
        return {leaf for k, v in node.items() for leaf in _leaves(v, f"{prefix}.{k}" if prefix else k)}
    return {prefix}


class Definitions:
    """definitions.yaml with access tracking, so a key no step reads is caught rather than trusted."""

    def __init__(self, path=DEFINITIONS):
        self._data = yaml.safe_load(Path(path).read_text())
        self.used = set()

    def _get(self, dotted):
        node = self._data
        for key in dotted.split("."):
            node = node[key]
        return node

    def __call__(self, dotted):
        node = self._get(dotted)
        self.used |= _leaves(node, dotted)
        return node

    def all_keys(self):
        return _leaves(self._data, "")

    def used_values(self):
        return {k: self._get(k) for k in sorted(self.used)}


def step_dirs(script_file, cfg):
    """(intermediate_phi/<step>/, final_no_phi/<step>/, final_no_phi/logs/) for a NN_name script, created."""
    step = Path(script_file).stem
    if not re.match(r"^\d{2}_", step):
        raise ValueError(f"step scripts are named NN_name, got {step!r}")
    out = Path(cfg["output_root"])
    dirs = (out / "intermediate_phi" / step, out / "final_no_phi" / step, out / "final_no_phi" / "logs")
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def suppress(n, threshold):
    return f"<{threshold}" if 0 < n < threshold else str(n)


def _git_sha():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"


class Step:
    """Everything a pipeline step shares: config, definitions, output folders and a DuckDB connection
    with the named CLIF tables as views. `finish` writes the outputs every step produces."""

    def __init__(self, script_file, tables):
        self.name = Path(script_file).stem
        self.cfg = load_config()
        self.defs = Definitions()
        target = str(self.defs("clif_version"))
        if str(self.cfg["clif_version"]).split(".")[0] != target.split(".")[0]:
            raise SystemExit(f"config clif_version {self.cfg['clif_version']} but this pipeline targets "
                             f"CLIF {target}; refusing to run against tables of another major version")
        self.phi_dir, self.share_dir, self.log_dir = step_dirs(script_file, self.cfg)
        self.con = connect(self.cfg, self.defs, tables)

    def table(self, name, sql, **params):
        self.con.execute(f"CREATE TEMP TABLE {name} AS {sql}", params)

    def count(self, relation):
        return self.con.execute(f"SELECT count(*) FROM {relation}").fetchone()[0]

    def finish(self, output_table, counts):
        """Patient-level table -> intermediate_phi; suppressed counts, provenance, log -> final_no_phi."""
        self.con.table(output_table).write_parquet(str(self.phi_dir / f"{output_table}.parquet"))

        threshold = int(self.cfg["small_cell_threshold"])
        shown = {k: suppress(v, threshold) for k, v in counts.items()}
        (self.share_dir / "counts.csv").write_text("step,n\n" + "".join(f"{k},{v}\n" for k, v in shown.items()))

        provenance = {
            "site_id": self.cfg["site"],
            "code_version": _git_sha(),
            "clif_version": self.cfg["clif_version"],
            "clif_spec_ref": self.defs("clif_spec_ref"),
            "definition_version": self.defs("definition_version"),
            "dataset_version": self.cfg.get("dataset_version"),
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        (self.share_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

        columns = self.con.execute(f"SELECT column_name, column_type FROM (DESCRIBE {output_table})").fetchall()
        log = [f"{self.name} ok",
               *(f"count {k} = {v}" for k, v in shown.items()),
               *(f"column {c}: {t}" for c, t in columns),
               *(f"definition {k} = {json.dumps(v)}" for k, v in self.defs.used_values().items())]
        (self.log_dir / f"{self.name}.log").write_text("\n".join(log) + "\n")
        (self.log_dir / f"{self.name}.defs_used.json").write_text(json.dumps(sorted(self.defs.used), indent=2) + "\n")
        print(f"{self.name}: wrote {output_table}.parquet and {self.share_dir.name}/counts.csv")
