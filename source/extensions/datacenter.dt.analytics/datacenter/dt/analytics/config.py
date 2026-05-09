"""Paths, identifiers, and labels for the Boreas Operator extension.

All constants here are stable across the extension lifecycle. Paths
honor environment variables so the same extension binary can run
against any Boreas data root.
"""

import os
from pathlib import Path

from .log import logger

# Resolve the Boreas data root. Order of precedence:
#   1. DT_PROJ_ROOT environment variable (explicit override)
#   2. ~/298AB-dt-viewer (the user-home convention used in development)
# The default is logged at import time so the operator sees what was picked.
PROJ_ROOT = Path(os.environ.get("DT_PROJ_ROOT", str(Path.home() / "298AB-dt-viewer")))
RAW_DATA_DIR = PROJ_ROOT / "test_data"
STL_DIR      = PROJ_ROOT / "stl"
RESULTS_DIR  = PROJ_ROOT / "results"
USD_DIR      = Path(os.environ.get("DT_USD_DIR",     str(PROJ_ROOT / "outputs" / "usd_omniverse")))
METRICS_DIR  = Path(os.environ.get("DT_METRICS_DIR", str(PROJ_ROOT / "outputs" / "omniverse_predictions")))

logger.info("PROJ_ROOT resolved to %s (exists=%s)", PROJ_ROOT, PROJ_ROOT.exists())

# Datacenter rooms available for inspection.
SAMPLES = [0, 1, 2]
SAMPLE_LABELS = {0: "Room 0 (config 0)", 1: "Room 1 (config 1)", 2: "Room 2 (config 2)"}

# Surrogate models the operator can compare.
MODELS = ["fno_pred", "unet_pred"]
MODEL_LABELS = {"fno_pred": "FNO (28.3M params)", "unet_pred": "U-Net (22.6M params)"}
MODEL_SHORT  = {"fno_pred": "FNO",                "unet_pred": "U-Net"}

# CFD fields visualized.
FIELDS = ["T", "U_magnitude", "p"]
FIELD_LABELS = {"T": "Temperature", "U_magnitude": "Velocity Magnitude", "p": "Pressure"}
FIELD_UNITS  = {"T": "°C",     "U_magnitude": "m/s",                "p": "Pa"}

# Spatial constants.
# Center-to-center offset between GT and Prediction in side-by-side compose stages.
# Room is ~3.84 m wide in this axis, so 6 m leaves a 2 m visible gap edge-to-edge —
# close enough to compare without overlap, comfortable in the AVP headset at 1:1.
SIDE_BY_SIDE_OFFSET = 6.0

# Grid spacing in meters (matches generate_assets.SPACING).
SPACING_M = 0.04
