from utils import Definitions, check_version, load_config, step_dirs

cfg = load_config()
defs = Definitions()
check_version(cfg, defs)
phi_dir, share_dir, log_dir = step_dirs(__file__, cfg)
