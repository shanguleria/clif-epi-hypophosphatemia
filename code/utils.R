# Assumes the working directory is the project root; run_pipeline.{sh,ps1} guarantee it.
# Mirrors code/utils.py: CLIF_CONFIG selects the synthetic sandbox, output_root relocates output/.
ROOT <- normalizePath(".")
CONFIG <- file.path(ROOT, "config", "config.json")
REQUIRED <- c("site", "data_directory", "filetype", "timezone", "clif_version",
              "small_cell_threshold")

load_config <- function() {
  path <- Sys.getenv("CLIF_CONFIG", CONFIG)
  if (!file.exists(path)) {
    stop(path, " missing: copy config/config.example.json and edit it")
  }
  cfg <- jsonlite::fromJSON(path)
  missing <- setdiff(REQUIRED, names(cfg))
  if (length(missing)) stop(path, " lacks required keys: ", paste(missing, collapse = ", "))
  cfg$output_root <- if (is.null(cfg$output_root)) file.path(ROOT, "output") else
    normalizePath(file.path(dirname(path), cfg$output_root), mustWork = FALSE)
  cfg
}

step_dirs <- function(step, cfg) {
  if (!grepl("^[0-9]{2}_", step)) stop("step scripts are named NN_name, got ", step)
  dirs <- c(phi = file.path(cfg$output_root, "intermediate_phi", step),
            share = file.path(cfg$output_root, "final_no_phi", step),
            logs = file.path(cfg$output_root, "final_no_phi", "logs"))
  for (d in dirs) dir.create(d, recursive = TRUE, showWarnings = FALSE)
  dirs
}
