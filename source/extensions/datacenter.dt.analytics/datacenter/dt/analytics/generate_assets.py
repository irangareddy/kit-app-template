"""Offline asset generator for the Datacenter DT Viewer.

Reads raw artifacts from C:/Users/Ranga/298AB-dt-viewer/ and produces the
USD + metrics layout the extension UI expects:

    <USD_DIR>/sample{N}_ground_truth_{field}.usdc
    <METRICS_DIR>/sample{N}_metrics.json

Runs inside Kit because pxr and numpy are only available at runtime here.
"""

import json
import struct
from pathlib import Path


SPACING = 0.04
STRIDE = 8
SAMPLES = list(range(10))
FIELDS = ["T", "U_magnitude", "p"]
MODELS = ["unet", "fno", "pifno", "pi_unet", "transolver"]

DENORM_T = (39.0, 4.0)
DENORM_U = (1.5984, 1.3656)
DENORM_P = (6.1227, 4.1660)


def _read_stl(path):
    with open(path, "rb") as f:
        head = f.read(80)
        rest = f.read()

    if head[:5] == b"solid" and b"facet normal" in rest[:512]:
        text = (head + rest).decode("ascii", errors="replace")
        verts = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                parts = line.split()
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        return verts

    count = struct.unpack("<I", rest[:4])[0]
    data = rest[4:]
    verts = []
    for i in range(count):
        base = i * 50 + 12
        for j in range(3):
            x, y, z = struct.unpack_from("<fff", data, base + j * 12)
            verts.append((x, y, z))
    return verts


RESULTS_DIR_REL = "results"


def _field_array(target, field):
    import numpy as np

    if field == "T":
        return target[3] * DENORM_T[1] + DENORM_T[0]
    if field == "U_magnitude":
        U = target[:3] * DENORM_U[1] + DENORM_U[0]
        return np.sqrt(np.sum(U * U, axis=0))
    return target[4] * DENORM_P[1] + DENORM_P[0]


def _field_range(arr, lo_pct=1.0, hi_pct=99.0):
    """Robust percentile-based colormap range from the actual field values."""
    import numpy as np

    lo = float(np.percentile(arr, lo_pct))
    hi = float(np.percentile(arr, hi_pct))
    if hi - lo < 1e-6:
        hi = lo + 1.0
    return lo, hi


def _load_real_metrics(results_dir):
    """Load aggregate test-set metrics from the actual trained-model result JSONs.

    Returns a dict in the UI's expected shape. Values are REAL — computed across
    192 test samples during training on GB10. These are model-level metrics,
    not per-sample, so the same dict is returned for every sample.
    """
    model_files = {
        "UNet":       results_dir / "unet_fullres_results.json",
        "FNO":        results_dir / "fno_fullres_results.json",
        "PI-FNO":     results_dir / "pifno_fullres_results.json",
        "PI-UNet":    results_dir / "pi_unet_fullres_results.json",
        "Transolver": results_dir / "transolver_fullres_results.json",
    }

    # Require at least FNO + U-Net
    if not model_files["FNO"].exists() or not model_files["UNet"].exists():
        print(f"[dt.analytics] missing core results JSON(s) in {results_dir}")
        return None

    def entry(raw):
        pm = raw["physical_metrics"]
        return {
            "inference_ms": round(raw.get("inference", {}).get("latency_mean_ms", 0), 1),
            "T":  {"MAE": round(pm["temperature"].get("MAE_C", pm["temperature"].get("MAE", 0)), 4),
                   "R2": round(pm["temperature"]["R2"], 4)},
            "Ux": {"MAE": round(pm["velocity_x"].get("MAE_ms", pm["velocity_x"].get("MAE", 0)), 4),
                   "R2": round(pm["velocity_x"]["R2"], 4)},
            "Uy": {"MAE": round(pm["velocity_y"].get("MAE_ms", pm["velocity_y"].get("MAE", 0)), 4),
                   "R2": round(pm["velocity_y"]["R2"], 4)},
            "Uz": {"MAE": round(pm["velocity_z"].get("MAE_ms", pm["velocity_z"].get("MAE", 0)), 4),
                   "R2": round(pm["velocity_z"]["R2"], 4)},
            "p":  {"MAE": round(pm["pressure"].get("MAE_Pa", pm["pressure"].get("MAE", 0)), 4),
                   "R2": round(pm["pressure"]["R2"], 4)},
        }

    result = {}
    for label, path in model_files.items():
        if path.exists():
            with open(path) as f:
                result[label] = entry(json.load(f))
            print(f"[dt.analytics]   loaded metrics for {label}")
        else:
            print(f"[dt.analytics]   skipping {label} (no JSON)")
    return result


def _attach_sample_ranges(metrics, target):
    """Add real per-sample gt_range to each field, computed from the actual sample."""
    import numpy as np

    T = target[3] * DENORM_T[1] + DENORM_T[0]
    Ux = target[0] * DENORM_U[1] + DENORM_U[0]
    Uy = target[1] * DENORM_U[1] + DENORM_U[0]
    Uz = target[2] * DENORM_U[1] + DENORM_U[0]
    P = target[4] * DENORM_P[1] + DENORM_P[0]

    ranges = {
        "T":  [round(float(T.min()), 3), round(float(T.max()), 3)],
        "Ux": [round(float(Ux.min()), 3), round(float(Ux.max()), 3)],
        "Uy": [round(float(Uy.min()), 3), round(float(Uy.max()), 3)],
        "Uz": [round(float(Uz.min()), 3), round(float(Uz.max()), 3)],
        "p":  [round(float(P.min()), 3), round(float(P.max()), 3)],
    }
    out = {}
    for model_key, model_metrics in metrics.items():
        out[model_key] = dict(model_metrics)
        for fn, rng in ranges.items():
            entry = dict(model_metrics[fn])
            entry["gt_range"] = rng
            out[model_key][fn] = entry
    return out


# Colormap stops (RGB 0-1) from matplotlib's turbo and magma.
# Used instead of the discredited jet colormap — turbo is perceptually uniform
# with the familiar blue-low / red-high thermal intuition; magma is a
# sequential dark-to-bright ramp, appropriate for error magnitudes.
_TURBO_STOPS = [
    (0.0000, (0.18995, 0.07176, 0.23217)),
    (0.0625, (0.25107, 0.25237, 0.63374)),
    (0.1250, (0.27628, 0.42118, 0.89123)),
    (0.1875, (0.25862, 0.57958, 0.99876)),
    (0.2500, (0.15844, 0.73551, 0.92305)),
    (0.3125, (0.09267, 0.86554, 0.76204)),
    (0.3750, (0.19659, 0.94901, 0.59466)),
    (0.4375, (0.42778, 0.99419, 0.38575)),
    (0.5000, (0.64362, 0.98999, 0.23356)),
    (0.5625, (0.80473, 0.92452, 0.20459)),
    (0.6250, (0.93301, 0.81236, 0.22667)),
    (0.6875, (0.99314, 0.67408, 0.20348)),
    (0.7500, (0.99163, 0.50980, 0.12762)),
    (0.8125, (0.94407, 0.33951, 0.05475)),
    (0.8750, (0.81608, 0.19431, 0.01715)),
    (0.9375, (0.65549, 0.08437, 0.00810)),
    (1.0000, (0.47960, 0.01583, 0.01055)),
]
_MAGMA_STOPS = [
    (0.0000, (0.00146, 0.00047, 0.01387)),
    (0.0714, (0.05174, 0.03225, 0.15080)),
    (0.1429, (0.13537, 0.06495, 0.32195)),
    (0.2143, (0.24282, 0.07406, 0.45343)),
    (0.2857, (0.35478, 0.07815, 0.50408)),
    (0.3571, (0.46591, 0.09423, 0.51619)),
    (0.4286, (0.57775, 0.11912, 0.50672)),
    (0.5000, (0.69128, 0.13689, 0.47549)),
    (0.5714, (0.80227, 0.17007, 0.42029)),
    (0.6429, (0.89409, 0.25388, 0.35358)),
    (0.7143, (0.95641, 0.38074, 0.30154)),
    (0.7857, (0.98614, 0.53464, 0.29983)),
    (0.8571, (0.99403, 0.68962, 0.38228)),
    (0.9286, (0.99344, 0.84673, 0.52398)),
    (1.0000, (0.98705, 0.99130, 0.74941)),
]


def _apply_cmap(vals, vmin, vmax, stops):
    """Map scalar values to RGB via piecewise-linear LUT on the given stops."""
    import numpy as np

    t = np.clip((vals - vmin) / max(vmax - vmin, 1e-6), 0.0, 1.0)
    xs = np.array([s[0] for s in stops], dtype=np.float32)
    ys = np.array([s[1] for s in stops], dtype=np.float32)  # (N, 3)
    r = np.interp(t, xs, ys[:, 0])
    g = np.interp(t, xs, ys[:, 1])
    b = np.interp(t, xs, ys[:, 2])
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def _error_array(pred, target, field):
    """|pred - gt| in physical units, shape (D, H, W)."""
    import numpy as np

    pred_phys = _field_array(pred, field)
    gt_phys = _field_array(target, field)
    return np.abs(pred_phys - gt_phys)


def _write_field_stage(out_path, stl_data, arr, vmin, vmax, cmap="turbo"):
    """Shared USD emitter: STL geometry + colored point cloud of a (D,H,W) array."""
    import numpy as np
    from pxr import Usd, UsdGeom, Vt, Gf

    sub = arr[::STRIDE, ::STRIDE, ::STRIDE]
    D, H, W = sub.shape

    ii, jj, kk = np.mgrid[0:D, 0:H, 0:W]
    pos = np.stack(
        [
            kk.flatten() * SPACING * STRIDE,
            jj.flatten() * SPACING * STRIDE,
            ii.flatten() * SPACING * STRIDE,
        ],
        axis=-1,
    ).astype(np.float32)

    vals = sub.flatten().astype(np.float32)
    stops = _MAGMA_STOPS if cmap == "magma" else _TURBO_STOPS
    col = _apply_cmap(vals, vmin, vmax, stops)
    widths = np.full(vals.shape, SPACING * STRIDE * 0.6, dtype=np.float32)

    stage = Usd.Stage.CreateNew(str(out_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetMetadata("metersPerUnit", 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Xform.Define(stage, "/World/Geometry")

    for name, verts in stl_data.items():
        mesh = UsdGeom.Mesh.Define(stage, f"/World/Geometry/{name}")
        mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*v) for v in verts]))
        nt = len(verts) // 3
        mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(list(range(len(verts)))))
        mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3] * nt))
        mesh.GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0.55, 0.55, 0.6)]))

    pts = UsdGeom.Points.Define(stage, "/World/Field")
    pts.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(pos))
    pts.GetWidthsAttr().Set(Vt.FloatArray.FromNumpy(widths))
    pts.CreateDisplayColorPrimvar(UsdGeom.Tokens.vertex).Set(
        Vt.Vec3fArray.FromNumpy(col)
    )

    stage.GetRootLayer().Save()
    return len(pos)


def _write_sample_stage(out_path, stl_data, data_5ch, field):
    """Emit a stage using the field value from a (5, D, H, W) normalized array."""
    arr = _field_array(data_5ch, field)
    vmin, vmax = _field_range(arr)
    return _write_field_stage(out_path, stl_data, arr, vmin, vmax)


def _write_error_stage(out_path, stl_data, pred, target, field):
    """Emit an error-map stage: |pred - gt| in physical units, magma colormap."""
    arr = _error_array(pred, target, field)
    vmin, vmax = 0.0, max(float(arr.max()) * 1.01, 1e-3)
    return _write_field_stage(out_path, stl_data, arr, vmin, vmax, cmap="magma")


def generate(raw_data_dir, stl_dir, usd_dir, metrics_dir, results_dir, force=False):
    raw_data_dir = Path(raw_data_dir)
    stl_dir = Path(stl_dir)
    usd_dir = Path(usd_dir)
    metrics_dir = Path(metrics_dir)
    results_dir = Path(results_dir)

    usd_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    marker = usd_dir / ".generated"
    if marker.exists() and not force:
        return False

    import numpy as np

    print(f"[dt.analytics] Generating scene assets -> {usd_dir}")

    base_metrics = _load_real_metrics(results_dir)
    if base_metrics is None:
        print(f"[dt.analytics] ERROR: real metrics unavailable — refusing to write fake metrics")
        return False

    stl_data = {}
    for stl_path in sorted(stl_dir.glob("*.stl")):
        verts = _read_stl(str(stl_path))
        stl_data[stl_path.stem] = verts
        print(f"[dt.analytics]   STL {stl_path.name}: {len(verts)} verts")

    pred_dir = raw_data_dir.parent / "outputs" / "predictions"

    for idx in SAMPLES:
        target_path = raw_data_dir / "targets" / f"sample_{idx:04d}.npy"
        if not target_path.exists():
            print(f"[dt.analytics]   missing {target_path.name}, skipping")
            continue
        target = np.load(target_path)

        for field in FIELDS:
            out_path = usd_dir / f"sample{idx}_ground_truth_{field}.usdc"
            n = _write_sample_stage(out_path, stl_data, target, field)
            print(f"[dt.analytics]   wrote {out_path.name}: {n} pts")

        for model in MODELS:
            pred_path = pred_dir / f"sample_{idx:04d}_{model}.npy"
            if not pred_path.exists():
                continue
            pred = np.load(pred_path)
            for field in FIELDS:
                out_pred = usd_dir / f"sample{idx}_{model}_pred_{field}.usdc"
                n = _write_sample_stage(out_pred, stl_data, pred, field)
                print(f"[dt.analytics]   wrote {out_pred.name}: {n} pts")

                out_err = usd_dir / f"sample{idx}_{model}_error_{field}.usdc"
                n = _write_error_stage(out_err, stl_data, pred, target, field)
                print(f"[dt.analytics]   wrote {out_err.name}: {n} pts (error)")

        sample_metrics = _attach_sample_ranges(base_metrics, target)
        (metrics_dir / f"sample{idx}_metrics.json").write_text(
            json.dumps(sample_metrics, indent=2)
        )

    marker.touch()
    print(f"[dt.analytics] Done.")
    return True
