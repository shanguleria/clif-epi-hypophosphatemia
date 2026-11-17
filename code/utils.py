import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

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

    def __call__(self, dotted):
        node = self._data
        for key in dotted.split("."):
            node = node[key]
        self.used |= _leaves(node, dotted)
        return node

    def all_keys(self):
        return _leaves(self._data, "")


def check_version(cfg, defs):
    target = str(defs("clif_version"))
    if str(cfg["clif_version"]).split(".")[0] != target.split(".")[0]:
        raise SystemExit(f"config clif_version {cfg['clif_version']} but this pipeline targets CLIF "
                         f"{target}; refusing to run against tables of another major version")


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


def provenance(cfg, defs):
    try:
        sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sha = "uncommitted"
    return {
        "site_id": cfg["site"],
        "code_version": sha,
        "clif_version": cfg["clif_version"],
        "clif_spec_ref": defs("clif_spec_ref"),
        "definition_version": defs("definition_version"),
        "dataset_version": cfg.get("dataset_version"),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def write_step_log(log_dir, step, lines, defs):
    (log_dir / f"{step}.log").write_text("\n".join(lines) + "\n")
    (log_dir / f"{step}.defs_used.json").write_text(json.dumps(sorted(defs.used), indent=2) + "\n")
