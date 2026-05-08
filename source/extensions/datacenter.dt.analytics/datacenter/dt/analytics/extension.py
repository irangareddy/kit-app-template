"""Datacenter Digital Twin Analytics Extension for Omniverse Kit.

Side-by-side GT vs Prediction comparison with color-coded metrics.
"""

import os
import json

import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Usd, UsdGeom, Gf, Sdf

from . import generate_assets
from .config import (
    PROJ_ROOT, RAW_DATA_DIR, STL_DIR, RESULTS_DIR, USD_DIR, METRICS_DIR,
    SAMPLES, SAMPLE_LABELS,
    MODELS, MODEL_LABELS, MODEL_SHORT,
    FIELDS, FIELD_LABELS, FIELD_UNITS,
    SIDE_BY_SIDE_OFFSET,
)
from .agent import Agent
from .denormalize import denormalize_field
from .view_state import ViewState
from .prompts import LLM_MODEL, AGENT_MAX_STEPS, SYSTEM_PROMPT, TOOL_SCHEMAS
from .log import logger
from .theme import (
    Color, Font,
    r2_color as _r2_color, r2_label as _r2_label, winner_arrow as _winner_arrow,
)

# Backwards-compat aliases (existing method bodies still reference bare names).
GREEN     = Color.GREEN_PRIMARY
ACCENT    = Color.GREEN_ACCENT
SECONDARY = Color.SECONDARY
RED       = Color.RED
YELLOW    = Color.YELLOW
WHITE     = Color.WHITE
GRAY      = Color.GRAY
DARK_BG   = Color.DARK_BG
CARD_BG   = Color.CARD_BG
CYAN      = Color.CYAN

FS_TITLE    = Font.TITLE
FS_SUBTITLE = Font.SECTION   # collapsed: original 14 -> SECTION
FS_SECTION  = Font.SECTION
FS_BODY     = Font.BODY
FS_LABEL    = Font.LABEL
FS_CAPTION  = Font.CAPTION
FS_FOOTER   = 10


class DatacenterDTAnalyticsExtension(omni.ext.IExt):
    WINDOW_TITLE = "Boreas Operator"
    MENU_PATH = f"Window/{WINDOW_TITLE}"

    def on_startup(self, ext_id):
        self._window = ui.Window(
            self.WINDOW_TITLE,
            width=420,
            height=820,
            position_x=40,
            position_y=80,
        )
        try:
            self._window.dock_order = 0
            self._window.deferred_dock_in("Property")
        except Exception as e:
            logger.debug(f"dock setup skipped: {e}")
        self._window.visible = True
        logger.debug(f"window '{self.WINDOW_TITLE}' created, visible={self._window.visible}")
        self.state = ViewState()
        self._metrics = {}
        self._laptop_latency = {}  # measured on this 5080 — filled by _load_metrics
        self._load_metrics()
        self._build_ui()
        self._register_menu()

    def on_shutdown(self):
        self._unregister_menu()
        if self._window:
            self._window.destroy()
            self._window = None

    def _register_menu(self):
        try:
            import omni.kit.menu.utils as menu_utils
            from omni.kit.menu.utils import MenuItemDescription

            self._menu_items = [
                MenuItemDescription(
                    name=self.WINDOW_TITLE,
                    onclick_fn=self._toggle_window,
                    ticked=True,
                    ticked_fn=lambda: bool(self._window and self._window.visible),
                )
            ]
            menu_utils.add_menu_items(self._menu_items, "Window")
        except Exception as e:
            logger.debug(f"could not register Window menu: {e}")
            self._menu_items = None

    def _unregister_menu(self):
        if getattr(self, "_menu_items", None):
            try:
                import omni.kit.menu.utils as menu_utils
                menu_utils.remove_menu_items(self._menu_items, "Window")
            except Exception:
                pass
            self._menu_items = None

    def _toggle_window(self):
        if self._window:
            self._window.visible = not self._window.visible

    def _load_metrics(self):
        for idx in SAMPLES:
            path = METRICS_DIR / f"sample{idx}_metrics.json"
            if path.exists():
                with open(str(path)) as f:
                    self._metrics[idx] = json.load(f)

        # Real measured latencies from the 5080 inference run
        summary = PROJ_ROOT / "outputs" / "predictions" / "inference_summary.json"
        if summary.exists():
            try:
                with open(summary) as f:
                    data = json.load(f)
                lat = data.get("latency_ms", {})
                for k in ("unet", "fno"):
                    vs = lat.get(k, [])
                    if vs:
                        self._laptop_latency[k] = round(sum(vs) / len(vs), 1)
            except Exception:
                pass

    def _ensure_generated(self):
        marker = USD_DIR / ".generated"
        if marker.exists():
            return
        try:
            generate_assets.generate(
                RAW_DATA_DIR, STL_DIR, USD_DIR, METRICS_DIR, RESULTS_DIR
            )
            self._load_metrics()
        except Exception as e:
            import traceback
            logger.warning(f"generate_assets failed: {e}")
            traceback.print_exc()

    def _load_single(self, model, field, is_error=False, is_iso=False):
        if is_error:
            tag = "fno" if model == "fno_pred" else "unet"
            fname = f"sample{self.state.sample}_{tag}_error_{field}.usdc"
        elif is_iso:
            fname = f"sample{self.state.sample}_{model}_T_iso.usdc"
        else:
            fname = f"sample{self.state.sample}_{model}_{field}.usdc"
        return USD_DIR / fname

    def _load_comparison_scene(self):
        """Load GT and prediction side-by-side in a single USD stage."""
        field = self.state.field
        model = self.state.model
        idx = self.state.sample

        gt_path = self._load_single("ground_truth", field)
        pred_path = self._load_single(model, field)
        err_path = self._load_single(model, field, is_error=True) if self.state.show_error else None

        logger.debug(f"_load_comparison_scene sample={idx} field={field} model={model}")
        logger.debug(f"GT   : {gt_path}  exists={gt_path.exists()}")
        logger.debug(f"Pred : {pred_path}  exists={pred_path.exists()}")
        if err_path:
            logger.debug(f"Err  : {err_path}  exists={err_path.exists()}")
        if not gt_path.exists() or not pred_path.exists():
            logger.warning("ABORT \u2014 missing GT or Prediction file")
            return

        try:
            err_tag = "_err" if (self.state.show_error and err_path and err_path.exists()) else ""
            compose_path = USD_DIR / f"_compose_s{idx}_{model}_{field}{err_tag}.usda"
            # Build in-memory to avoid USD's layer registry collision, then Export.
            stage = Usd.Stage.CreateInMemory()
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
            UsdGeom.SetStageMetersPerUnit(stage, 1.0)
            UsdGeom.Xform.Define(stage, "/DatacenterComparison")

            gt_ref  = gt_path.as_posix()
            pred_ref = pred_path.as_posix()
            logger.debug(f"ref GT   = {gt_ref}")
            logger.debug(f"ref Pred = {pred_ref}")

            gt_xf = UsdGeom.Xform.Define(stage, "/DatacenterComparison/GroundTruth")
            gt_xf.GetPrim().GetReferences().AddReference(gt_ref)
            gt_xf.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0))

            pred_xf = UsdGeom.Xform.Define(stage, "/DatacenterComparison/Prediction")
            pred_xf.GetPrim().GetReferences().AddReference(pred_ref)
            pred_xf.AddTranslateOp().Set(Gf.Vec3d(0, SIDE_BY_SIDE_OFFSET, 0))

            if self.state.show_error and err_path and err_path.exists():
                err_xf = UsdGeom.Xform.Define(stage, "/DatacenterComparison/ErrorMap")
                err_xf.GetPrim().GetReferences().AddReference(err_path.as_posix())
                err_xf.AddTranslateOp().Set(Gf.Vec3d(0, SIDE_BY_SIDE_OFFSET * 2, 0))

            stage.GetRootLayer().Export(str(compose_path))
            logger.debug(f"composed stage saved -> {compose_path}")
            omni.usd.get_context().open_stage(str(compose_path))
            self._frame_all()
        except Exception as e:
            import traceback
            logger.warning(f"_load_comparison_scene ERROR: {e}")
            traceback.print_exc()
            return

        self._rebuild_metrics_panel()

    def _load_single_scene(self):
        """Load a single USD file."""
        if self.state.show_isosurface:
            path = self._load_single(self.state.model, "T", is_iso=True)
        elif self.state.show_error:
            path = self._load_single(self.state.model, self.state.field, is_error=True)
        else:
            path = self._load_single(self.state.model, self.state.field)

        logger.debug(f"_load_single_scene -> {path}  exists={path.exists()}")
        if path.exists():
            omni.usd.get_context().open_stage(str(path))
            self._frame_all()
        else:
            logger.warning("ABORT \u2014 file not found (if Isosurface Mode is checked, iso USDs aren't generated yet)")
        self._rebuild_metrics_panel()

    def _load_gt_only(self):
        """Load ground truth only."""
        self._ensure_generated()
        path = self._load_single("ground_truth", self.state.field)
        if path.exists():
            omni.usd.get_context().open_stage(str(path))
            self._frame_all()
        self._rebuild_metrics_panel()

    def _frame_all(self):
        """Frame the viewport on the user scene, deferred so references resolve first."""
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            logger.debug("_frame_all: no stage")
            return

        user_roots = [str(p.GetPath()) for p in stage.GetPseudoRoot().GetChildren()
                      if not str(p.GetPath()).startswith(("/Omni", "/Render"))]
        if not user_roots:
            logger.debug("_frame_all: no user-scene roots")
            return

        # Force any payloads/references on these prims to load synchronously.
        from pxr import Sdf
        stage.LoadAndUnload({Sdf.Path(p) for p in user_roots}, set())

        try:
            import omni.kit.commands
            omni.kit.commands.execute(
                "SelectPrims", old_selected_paths=[], new_selected_paths=user_roots,
                expand_in_stage=True,
            )
        except Exception as e:
            logger.warning(f"SelectPrims failed: {e}")

        import omni.kit.app
        from pxr import UsdGeom, Gf
        app = omni.kit.app.get_app()

        async def _deferred():
            # Async fire-and-forget would silently swallow exceptions in earlier
            # versions; wrap so failures land in the boreas.operator log.
            try:
                # Wait enough frames for references + RTX to ingest geometry
                for _ in range(12):
                    await app.next_update_async()

                # Measure bbox NOW (references should be resolved)
                cache = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_], useExtentsHint=True)
                bbox = Gf.BBox3d()
                for path in user_roots:
                    prim = stage.GetPrimAtPath(path)
                    if prim:
                        bbox = Gf.BBox3d.Combine(bbox, cache.ComputeWorldBound(prim))
                r = bbox.ComputeAlignedRange()

                if not r.IsEmpty():
                    try:
                        from omni.kit.viewport.utility import frame_viewport_selection, get_active_viewport
                        frame_viewport_selection(get_active_viewport())
                        logger.debug(f"_frame_all: framed via selection (bbox size={r.GetSize()})")
                        return
                    except Exception as e:
                        logger.warning(f"frame_viewport_selection failed: {e}")

                # Fallback: hardcode a known-good camera pose for our fixed data layout.
                # GT spans ~X 0-38, Y 0-4, Z 0-3.  Pred offset +50 in Y.
                logger.debug("_frame_all: bbox still empty, using manual camera")
                cam = stage.GetPrimAtPath("/OmniverseKit_Persp")
                if cam:
                    api = UsdGeom.XformCommonAPI(cam)
                    # Eye position — isometric above +X +Y, looking at center (~19, 27, 1.5)
                    api.SetTranslate(Gf.Vec3d(-20.0, -25.0, 40.0))
                    # Rotation in degrees (X tilt, Y yaw, Z roll) that orients the default
                    # -Z camera forward toward the scene center
                    api.SetRotate(Gf.Vec3f(55.0, 0.0, -30.0))
            except Exception:
                logger.exception("_frame_all _deferred crashed")

        import asyncio
        asyncio.ensure_future(_deferred())

    def _on_load(self):
        logger.debug("========== LOAD SCENE ==========")
        logger.debug(f"sample       = {self.state.sample} ({SAMPLE_LABELS.get(self.state.sample)})")
        logger.debug(f"field        = {self.state.field}")
        logger.debug(f"model        = {self.state.model}")
        logger.debug(f"comparison   = {self.state.comparison_mode}")
        logger.warning(f"show_error   = {self.state.show_error}")
        logger.debug(f"isosurface   = {self.state.show_isosurface}")
        logger.debug(f"USD_DIR      = {USD_DIR}")
        logger.debug(f"RAW_DATA_DIR = {RAW_DATA_DIR}")
        logger.debug(f"OPENAI_API_KEY set = {bool(os.environ.get('OPENAI_API_KEY'))}")
        self._ensure_generated()
        if self.state.comparison_mode:
            self._load_comparison_scene()
        else:
            self._load_single_scene()

    # ------------------------------------------------------------------ NL query

    _SPACING_M = 0.04  # grid spacing in meters (matches generate_assets.SPACING)

    _LLM_MODEL = LLM_MODEL
    _AGENT_MAX_STEPS = AGENT_MAX_STEPS
    _AGENT_SYSTEM_PROMPT = SYSTEM_PROMPT
    _AGENT_TOOLS = TOOL_SCHEMAS

    def _compute_query(self, op, field, room=None):
        import numpy as np
        idx = self.state.sample if room is None else int(room)
        target_path = RAW_DATA_DIR / "targets" / f"sample_{idx:04d}.npy"
        if not target_path.exists():
            return None
        target = np.load(target_path)
        arr, unit = denormalize_field(target, field)
        flat_idx = int(np.argmax(arr) if op == "max" else np.argmin(arr))
        ind = np.unravel_index(flat_idx, arr.shape)
        value = float(arr[ind])
        world = (ind[2] * self._SPACING_M,  # X from W-index
                 ind[1] * self._SPACING_M,  # Y from H-index
                 ind[0] * self._SPACING_M)  # Z from D-index
        return value, world, unit, ind

    def _mark_and_frame(self, world_xyz):
        import omni.usd
        from pxr import Usd, UsdGeom, Gf
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            return False
        marker_path = "/World/QueryMarker"
        prim = stage.GetPrimAtPath(marker_path)
        if not prim:
            marker = UsdGeom.Sphere.Define(stage, marker_path)
            marker.CreateRadiusAttr(0.35)
            marker.GetDisplayColorAttr().Set([Gf.Vec3f(1.0, 0.15, 0.15)])
            prim = marker.GetPrim()
        xformable = UsdGeom.Xformable(prim)
        xformable.ClearXformOpOrder()
        xformable.AddTranslateOp().Set(Gf.Vec3d(*world_xyz))
        try:
            import omni.kit.commands
            omni.kit.commands.execute(
                "SelectPrims",
                old_selected_paths=[], new_selected_paths=[marker_path], expand_in_stage=True,
            )
        except Exception:
            pass
        try:
            from omni.kit.viewport.utility import frame_viewport_selection, get_active_viewport
            frame_viewport_selection(get_active_viewport())
        except Exception as e:
            logger.warning(f"frame_viewport_selection failed: {e}")
        return True

    def _on_query(self, text):
        text = (text or "").strip()
        if not text:
            return
        if not os.environ.get("OPENAI_API_KEY"):
            self._query_result_label.text = "OpenAI API key required (set OPENAI_API_KEY)."
            self._query_result_label.set_style({"color": Color.RED, "font_size": Font.BODY})
            return
        # Mark busy: clear old answer, show distinct loading state, disable Ask button.
        # An asyncio yield lets Kit repaint these changes BEFORE the blocking agent call.
        self._query_running = True
        self._busy_query_text = text
        self._query_result_label.text = f"⏳  Thinking…  ({text[:80]})"
        self._query_result_label.set_style({"color": Color.YELLOW, "font_size": Font.BODY})
        if hasattr(self, "_btn_ask"):
            self._btn_ask.enabled = False
        import asyncio, omni.kit.app

        async def _deferred_run():
            try:
                # Yield once so the busy state actually paints before the blocking call.
                await omni.kit.app.get_app().next_update_async()
                answer, trace = self._run_agent(self._busy_query_text)
                trace_line = "  →  ".join(trace) if trace else "no tools called"
                self._query_result_label.text = f"{answer}\n\n[agent: {trace_line}]"
                self._query_result_label.set_style({"color": Color.WHITE, "font_size": Font.BODY})
            except Exception:
                logger.exception("agent run failed")
                self._query_result_label.text = "Agent failed (see boreas.operator log)."
                self._query_result_label.set_style({"color": Color.RED, "font_size": Font.BODY})
            finally:
                self._query_running = False
                if hasattr(self, "_btn_ask"):
                    self._btn_ask.enabled = True

        asyncio.ensure_future(_deferred_run())

    def _run_agent(self, user_text):
        """Delegate to the Agent module. Returns (final_text, trace_list)."""
        if not hasattr(self, "_agent"):
            self._agent = Agent(
                dispatch_tool=self._dispatch_tool,
                describe_view=self._tool_describe_current_view,
            )
        return self._agent.run(user_text)

    # ----------------------------------------------------------------- tool impls

    def _dispatch_tool(self, name, args):
        fn = {
            "describe_current_view": lambda: self._tool_describe_current_view(),
            "set_room":              lambda: self._tool_set_room(args.get("room", 0)),
            "set_field":             lambda: self._tool_set_field(args.get("field", "T")),
            "set_surrogate":         lambda: self._tool_set_surrogate(args.get("model", "unet")),
            "find_extremum":         lambda: self._tool_find_extremum(args.get("op", "max"), args.get("field", "T"), args.get("room")),
            "get_room_stats":        lambda: self._tool_get_room_stats(args.get("field", "T"), args.get("room")),
            "get_model_comparison":  lambda: self._tool_get_model_comparison(args.get("field")),
            "frame_camera":          lambda: self._tool_frame_camera(args.get("x", 0), args.get("y", 0), args.get("z", 0), args.get("label")),
            "load_scene":            lambda: self._tool_load_scene(),
        }.get(name)
        if fn is None:
            return {"error": f"unknown tool '{name}'"}
        try:
            return fn()
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    def _tool_describe_current_view(self):
        return {
            "room": self.state.sample,
            "room_label": SAMPLE_LABELS.get(self.state.sample, f"Sample {self.state.sample}"),
            "field": self.state.field,
            "surrogate": "unet" if self.state.model == "unet_pred" else "fno",
            "comparison_mode": self.state.comparison_mode,
            "show_error_map": self.state.show_error,
        }

    def _tool_set_room(self, room):
        if room not in SAMPLES:
            return {"error": f"room must be one of {SAMPLES}"}
        self.state.sample = int(room)
        return {"ok": True, "room": self.state.sample}

    def _tool_set_field(self, field):
        if field not in FIELDS:
            return {"error": f"field must be one of {FIELDS}"}
        self.state.field = field
        return {"ok": True, "field": field}

    def _tool_set_surrogate(self, model):
        if model not in ("fno", "unet"):
            return {"error": "model must be 'fno' or 'unet'"}
        self.state.model = f"{model}_pred"
        return {"ok": True, "model": model}

    def _tool_find_extremum(self, op, field, room=None):
        idx = self.state.sample if room is None else int(room)
        if idx not in SAMPLES:
            return {"error": f"room must be one of {SAMPLES}"}
        res = self._compute_query(op, field, room=idx)
        if res is None:
            return {"error": f"target data missing for room {idx}"}
        value, world, unit, ind = res
        return {
            "op": op, "field": field,
            "value": round(value, 3), "unit": unit,
            "world_xyz_m": [round(v, 3) for v in world],
            "grid_index_zyx": [int(ind[0]), int(ind[1]), int(ind[2])],
            "room": idx,
        }

    def _tool_get_room_stats(self, field, room=None):
        import numpy as np
        idx = self.state.sample if room is None else int(room)
        if idx not in SAMPLES:
            return {"error": f"room must be one of {SAMPLES}"}
        target_path = RAW_DATA_DIR / "targets" / f"sample_{idx:04d}.npy"
        if not target_path.exists():
            return {"error": "target not on disk"}
        target = np.load(target_path)
        arr, unit = denormalize_field(target, field)
        return {
            "field": field, "unit": unit, "room": idx,
            "min":  round(float(arr.min()),  3),
            "max":  round(float(arr.max()),  3),
            "mean": round(float(arr.mean()), 3),
            "std":  round(float(arr.std()),  3),
        }

    def _tool_get_model_comparison(self, field=None):
        idx = self.state.sample
        m = self._metrics.get(idx)
        if not m:
            return {"error": "no metrics loaded"}
        fno, unet = m.get("FNO", {}), m.get("UNet", {})
        out = {
            "latency_ms": {"fno": fno.get("inference_ms"), "unet": unet.get("inference_ms")},
            "laptop_measured_latency_ms": self._laptop_latency,
        }
        fields = [field] if field in ("T", "Ux", "Uy", "Uz", "p") else ["T", "Ux", "Uy", "Uz", "p"]
        out["per_field"] = {
            fn: {"fno":  {"MAE": fno.get(fn, {}).get("MAE"),  "R2": fno.get(fn, {}).get("R2")},
                 "unet": {"MAE": unet.get(fn, {}).get("MAE"), "R2": unet.get(fn, {}).get("R2")}}
            for fn in fields
        }
        return out

    def _tool_frame_camera(self, x, y, z, label=None):
        ok = self._mark_and_frame((float(x), float(y), float(z)))
        return {"ok": bool(ok), "x": x, "y": y, "z": z, "label": label}

    def _tool_load_scene(self):
        self._ensure_generated()
        if self.state.comparison_mode:
            self._load_comparison_scene()
        else:
            self._load_single_scene()
        return {"ok": True, "loaded_view": self._tool_describe_current_view()}

    def _rebuild_metrics_panel(self):
        """Unified, scannable metrics view."""
        self._metrics_frame.clear()
        idx = self.state.sample
        field = self.state.field
        model = self.state.model

        with self._metrics_frame:
            with ui.VStack(spacing=10):
                self._section_view_header(idx, field, model)

                if idx not in self._metrics:
                    ui.Label("No metrics on disk. Click GT Only or Load Scene to generate.",
                             style={"color": RED, "font_size": FS_BODY})
                    return

                data = self._metrics[idx]
                fno = data.get("FNO", {})
                unet = data.get("UNet", {})

                self._section_winner_banner(fno, unet)
                self._section_accuracy_table(fno, unet, field)
                self._section_deployment(fno, unet)
                self._section_room_range(fno, unet, field)
                self._section_context_note()

    # ------------------------------------------------------------------ sections

    def _section_view_header(self, idx, field, model):
        """Compact current-view strip."""
        mode = "Side-by-Side" if self.state.comparison_mode else "Single"
        if self.state.show_error:
            mode += " + Error"
        if self.state.show_isosurface:
            mode = "Isosurface"

        with ui.ZStack(height=52):
            ui.Rectangle(style={"background_color": CARD_BG, "border_radius": 6})
            with ui.VStack(spacing=3):
                ui.Spacer(height=6)
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Label(
                        f"{SAMPLE_LABELS.get(idx, f'Sample {idx}')}  \u2022  "
                        f"{FIELD_LABELS[field]} ({FIELD_UNITS[field]})  \u2022  {mode}",
                        style={"font_size": FS_SECTION, "color": CYAN},
                    )
                with ui.HStack():
                    ui.Spacer(width=10)
                    if self.state.comparison_mode:
                        sub = f"Left: Ground Truth (OpenFOAM)    Right: {MODEL_SHORT[model]} prediction"
                    else:
                        sub = f"Showing: {MODEL_SHORT.get(model, 'Ground Truth')}"
                    ui.Label(sub, style={"font_size": FS_LABEL, "color": GRAY})

    def _section_winner_banner(self, fno, unet):
        """One-line verdict across all fields + latency."""
        fields = ["T", "Ux", "Uy", "Uz", "p"]
        unet_wins = 0
        for fn in fields:
            f_mae = fno.get(fn, {}).get("MAE")
            u_mae = unet.get(fn, {}).get("MAE")
            if f_mae is not None and u_mae is not None and u_mae < f_mae:
                unet_wins += 1
        f_ms = fno.get("inference_ms")
        u_ms = unet.get("inference_ms")
        latency_winner = "U-Net" if (f_ms is not None and u_ms is not None and u_ms < f_ms) else (
            "FNO" if (f_ms is not None and u_ms is not None and f_ms < u_ms) else None)

        with ui.ZStack(height=44):
            ui.Rectangle(style={"background_color": 0xFF1E3320, "border_radius": 6,
                                "border_color": GREEN, "border_width": 1})
            with ui.HStack():
                ui.Spacer(width=12)
                with ui.VStack(spacing=2):
                    ui.Spacer(height=6)
                    ui.Label(f"Overall  \u2014  U-Net wins {unet_wins} of {len(fields)} fields",
                             style={"font_size": FS_SECTION, "color": GREEN})
                    tag = (f"and is faster on training hardware (GB10)"
                           if latency_winner == "U-Net" else
                           f"and {latency_winner or 'both'} lead on latency")
                    ui.Label(tag, style={"font_size": FS_LABEL, "color": GRAY})

    def _section_accuracy_table(self, fno, unet, current_field):
        """Unified MAE + R² table, one row per field."""
        ui.Label("Per-field accuracy  \u2014  192 test rooms on GB10",
                 style={"font_size": FS_SECTION, "color": WHITE})

        with ui.HStack(height=20):
            ui.Label("  Field",          width=46, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("FNO MAE",          width=72, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("U-Net MAE",        width=72, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("FNO R\u00b2",       width=50, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("U-Net R\u00b2",     width=54, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("Win",              width=46, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})

        unit_for = {"T": "\u00b0C", "Ux": "m/s", "Uy": "m/s", "Uz": "m/s", "p": "Pa"}
        for fn in ["T", "Ux", "Uy", "Uz", "p"]:
            f_mae = fno.get(fn, {}).get("MAE")
            u_mae = unet.get(fn, {}).get("MAE")
            f_r2  = fno.get(fn, {}).get("R2")
            u_r2  = unet.get(fn, {}).get("R2")

            winner = _winner_arrow(f_mae, u_mae, lower_is_better=True) if (f_mae is not None and u_mae is not None) else "?"
            win_color = GREEN if winner == "U-Net" else ACCENT if winner == "FNO" else GRAY
            is_current = (fn == current_field) or (fn in ("Ux", "Uy", "Uz") and current_field == "U_magnitude")
            row_bg = 0xFF2F3A2F if is_current else 0x00000000  # subtle green-tinted highlight

            with ui.ZStack(height=24):
                ui.Rectangle(style={"background_color": row_bg, "border_radius": 3})
                with ui.HStack():
                    ui.Label(f"  {fn}",             width=46, style={"font_size": FS_BODY, "color": WHITE})
                    ui.Label(self._fmt_mae(f_mae, unit_for[fn]), width=72, alignment=ui.Alignment.RIGHT, style={"font_size": FS_BODY, "color": GRAY})
                    ui.Label(self._fmt_mae(u_mae, unit_for[fn]), width=72, alignment=ui.Alignment.RIGHT, style={"font_size": FS_BODY, "color": WHITE})
                    ui.Label(self._fmt_r2(f_r2),    width=50, alignment=ui.Alignment.RIGHT, style={"font_size": FS_BODY, "color": _r2_color(f_r2) if f_r2 is not None else GRAY})
                    ui.Label(self._fmt_r2(u_r2),    width=54, alignment=ui.Alignment.RIGHT, style={"font_size": FS_BODY, "color": _r2_color(u_r2) if u_r2 is not None else GRAY})
                    ui.Label(winner,                 width=46, alignment=ui.Alignment.RIGHT, style={"font_size": FS_LABEL, "color": win_color})

    def _section_deployment(self, fno, unet):
        """Training-hardware vs this-laptop latency comparison."""
        ui.Label("Deployment  \u2014  inference latency", style={"font_size": FS_SECTION, "color": WHITE})
        with ui.HStack(height=20):
            ui.Label("  Model",         width=76, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("Params",          width=60, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("GB10 paper",      width=78, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})
            ui.Label("5080 measured",   width=96, alignment=ui.Alignment.RIGHT, style={"font_size": FS_CAPTION, "color": GRAY})

        rows = [
            ("FNO",    "28.3 M", fno.get("inference_ms"),  self._laptop_latency.get("fno")),
            ("U-Net",  "22.6 M", unet.get("inference_ms"), self._laptop_latency.get("unet")),
        ]
        for name, params, gb10, laptop in rows:
            with ui.HStack(height=22):
                ui.Label(f"  {name}",                      width=76, style={"font_size": FS_BODY, "color": WHITE})
                ui.Label(params,                             width=60, alignment=ui.Alignment.RIGHT, style={"font_size": FS_BODY, "color": GRAY})
                ui.Label(f"{gb10} ms" if gb10 is not None else "\u2013",
                         width=78, alignment=ui.Alignment.RIGHT, style={"font_size": FS_BODY, "color": GRAY})
                ui.Label(f"{laptop} ms" if laptop is not None else "\u2013",
                         width=96, alignment=ui.Alignment.RIGHT,
                         style={"font_size": FS_BODY, "color": ACCENT if laptop is not None else GRAY})

    def _section_room_range(self, fno, unet, field):
        """Compact current-field GT range for the selected room."""
        sel = fno.get(field, fno.get("T", {})) or unet.get(field, unet.get("T", {}))
        gt_r = sel.get("gt_range") if sel else None
        if not gt_r or gt_r[0] == "?":
            return
        with ui.ZStack(height=28):
            ui.Rectangle(style={"background_color": CARD_BG, "border_radius": 6})
            with ui.HStack():
                ui.Spacer(width=10)
                ui.Label(f"This room \u2014 GT {FIELD_LABELS[field]} range:",
                         style={"font_size": FS_LABEL, "color": GRAY})
                ui.Spacer(width=6)
                ui.Label(f"[{gt_r[0]}, {gt_r[1]}] {FIELD_UNITS[field]}",
                         style={"font_size": FS_BODY, "color": WHITE})

    def _section_context_note(self):
        """Bottom caption about data source + resolution."""
        with ui.ZStack(height=52):
            ui.Rectangle(style={"background_color": 0xFF242430, "border_radius": 6})
            with ui.VStack(spacing=1):
                ui.Spacer(height=6)
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Label("Full-resolution grid: 80 \u00d7 96 \u00d7 960 = 7.37 M points / room",
                             style={"font_size": FS_CAPTION, "color": GRAY}, word_wrap=True)
                with ui.HStack():
                    ui.Spacer(width=10)
                    ui.Label("Dataset: NVIDIA + Wistron PhysicsNeMo-Datacenter-CFD (Apache-2.0)",
                             style={"font_size": FS_CAPTION, "color": GRAY}, word_wrap=True)

    # ------------------------------------------------------------------ format helpers

    @staticmethod
    def _fmt_mae(v, unit):
        if v is None:
            return "\u2013"
        return f"{v:.3f} {unit}"

    @staticmethod
    def _fmt_r2(v):
        if v is None:
            return "\u2013"
        return f"{v:.3f}"

    def _build_ui(self):
        with self._window.frame:
            with ui.VStack(spacing=6):

                # Header
                with ui.ZStack(height=50):
                    ui.Rectangle(style={"background_color": ACCENT, "border_radius": 8})
                    with ui.VStack():
                        ui.Spacer(height=6)
                        ui.Label("  Boreas Operator", style={"font_size": FS_TITLE, "color": WHITE})
                        ui.Label("  Datacenter operator console \u2014 ask the agent or drive the viewport directly", style={"font_size": FS_SUBTITLE, "color": 0xFFE8F5D0})

                ui.Spacer(height=4)

                # Controls
                with ui.CollapsableFrame("Controls", height=0, collapsed=False):
                    with ui.VStack(spacing=6):
                        with ui.HStack(height=26):
                            ui.Label("Room:", width=90, style={"font_size": 13},
                                     tooltip="Datacenter sample (rack-layout configuration). 3 of the 192 test rooms are pre-rendered for the demo.")
                            combo_s = ui.ComboBox(0, *[SAMPLE_LABELS.get(i, f"Sample {i}") for i in SAMPLES])
                            combo_s.model.add_item_changed_fn(lambda m, _: self._set("sample", m.get_item_value_model().as_int))

                        with ui.HStack(height=26):
                            ui.Label("Surrogate:", width=90, style={"font_size": 13},
                                     tooltip="Trained ML surrogate model. Boreas trains 6 models (FNO, U-Net, PI-FNO, PI-U-Net, Transolver, POD+MLP) — only FNO and U-Net have USD viewport assets in this build; the other 4 appear in the metrics tables.")
                            combo_m = ui.ComboBox(0, *[MODEL_LABELS[k] for k in MODELS])
                            combo_m.model.add_item_changed_fn(lambda m, _: self._set("model", m.get_item_value_model().as_int))

                        with ui.HStack(height=26):
                            ui.Label("Field:", width=90, style={"font_size": 13},
                                     tooltip="Which CFD field to visualize: T = temperature (degrees C), U_magnitude = airflow speed (m/s), p = static pressure (Pa).")
                            combo_f = ui.ComboBox(0, *[f"{FIELD_LABELS[k]} ({FIELD_UNITS[k]})" for k in FIELDS])
                            combo_f.model.add_item_changed_fn(lambda m, _: self._set("field", m.get_item_value_model().as_int))

                        ui.Spacer(height=2)

                        with ui.HStack(height=24, spacing=6):
                            cb1 = ui.CheckBox(width=18)
                            cb1.model.set_value(True)
                            cb1.model.add_value_changed_fn(lambda m: self._set("compare", m.as_bool))
                            ui.Label("Side-by-side (GT left | Pred right)", style={"font_size": 12},
                                     tooltip="Show ground truth alongside the prediction (offset 50 m). Off = prediction only. Independent of the other two checkboxes.")

                        with ui.HStack(height=24, spacing=6):
                            cb2 = ui.CheckBox(width=18)
                            cb2.model.set_value(False)
                            cb2.model.add_value_changed_fn(lambda m: self._set("error", m.as_bool))
                            ui.Label("Show Error Map (3rd row)", style={"font_size": 12},
                                     tooltip="Add a 3rd offset row showing per-voxel |Prediction - GT| as a magma colormap. Hot spots = where the surrogate is least accurate.")

                        with ui.HStack(height=24, spacing=6):
                            cb3 = ui.CheckBox(width=18)
                            cb3.model.set_value(False)
                            cb3.model.add_value_changed_fn(lambda m: self._set("iso", m.as_bool))
                            ui.Label("Isosurface Mode (T only)", style={"font_size": 12},
                                     tooltip="Render temperature as a marching-cubes isosurface mesh (solid 3D contour) instead of a colored point cloud. Currently only available for T; U and p don't have iso USDs in this build.")

                ui.Spacer(height=4)

                # Action buttons
                with ui.HStack(height=36, spacing=6):
                    btn_load = ui.Button(
                        "Load Scene",
                        style={"background_color": ACCENT, "color": WHITE,
                               "font_size": FS_BODY, "border_radius": 6},
                        tooltip="Apply the current Room / Surrogate / Field / checkbox selection: assemble the USD compose stage and frame the camera. Press this after changing any control.",
                    )
                    btn_load.set_clicked_fn(self._on_load)
                    btn_gt = ui.Button(
                        "GT Only",
                        style={"background_color": SECONDARY, "color": WHITE,
                               "font_size": FS_BODY, "border_radius": 6},
                        tooltip="Load only the ground-truth USD for the current Room and Field — no surrogate prediction, no error overlay, no isosurface. Useful as a clean reference view.",
                    )
                    btn_gt.set_clicked_fn(self._load_gt_only)

                ui.Spacer(height=4)

                # Ask the Twin — natural-language operator query over the surrogate.
                # Empty input by default; sample buttons below populate-and-submit.
                with ui.CollapsableFrame("Ask the Twin", height=0, collapsed=False):
                    with ui.VStack(spacing=6):

                        # Query input + Ask button.
                        with ui.HStack(height=28, spacing=6):
                            self._query_field = ui.StringField(height=26)
                            # Start empty — operator types or clicks a sample below.

                            def _submit_query(*_args):
                                self._on_query(self._query_field.model.get_value_as_string())

                            # Enter in the StringField triggers Ask.
                            self._query_field.model.add_end_edit_fn(_submit_query)

                            self._btn_ask = ui.Button(
                                "Ask",
                                width=72,
                                style={"background_color": GREEN, "color": WHITE,
                                       "font_size": FS_BODY, "border_radius": 6},
                                tooltip="Send the question to the Boreas Operator Agent. Agent uses GPT-4o + 9 tools to query the surrogate, drive the viewport, and answer in operator voice with ASHRAE thresholds.",
                            )
                            self._btn_ask.set_clicked_fn(_submit_query)

                        # Sample questions — one click populates the field and submits.
                        # Each question exercises a different tool combination so the
                        # demo can cover the agent surface in 5 clicks.
                        SAMPLE_QUERIES = [
                            "Where is the hottest spot in room 0 and what should I do?",
                            "Among rooms 0, 1, and 2, which has the most thermal stress?",
                            "Compare FNO and U-Net temperature accuracy across the test set.",
                            "What is the airflow distribution in room 1? Is it adequate?",
                            "Recommend immediate cooling actions for the current hotspot.",
                        ]

                        def _make_sample_runner(text):
                            def _run(*_args):
                                self._query_field.model.set_value(text)
                                self._on_query(text)
                            return _run

                        for sample in SAMPLE_QUERIES:
                            btn = ui.Button(
                                sample,
                                height=24,
                                style={"background_color": Color.SECONDARY,
                                       "color": Color.WHITE,
                                       "font_size": Font.LABEL,
                                       "border_radius": 4,
                                       "padding": 4},
                                tooltip="Click to send this question to the agent.",
                            )
                            btn.set_clicked_fn(_make_sample_runner(sample))

                        ui.Spacer(height=2)

                        # Answer area — empty at startup, fills with agent response.
                        self._query_result_label = ui.Label(
                            "",
                            style={"font_size": FS_BODY, "color": WHITE},
                            word_wrap=True,
                            height=0,
                        )

                ui.Spacer(height=4)

                # Metrics panel
                with ui.CollapsableFrame("Analytics & Metrics", height=0, collapsed=False):
                    self._metrics_frame = ui.VStack(spacing=4)

                # Initial metrics
                self._rebuild_metrics_panel()

                ui.Spacer(height=2)
                ui.Label("SJSU CMPE 298AB  |  NVIDIA PhysicsNeMo-Datacenter-CFD dataset (960 rooms, Apache-2.0)",
                         style={"font_size": 10, "color": 0xFF666666})

    def _set(self, key, value):
        if key == "sample":
            self.state.sample = SAMPLES[value]
        elif key == "model":
            self.state.model = MODELS[value]
        elif key == "field":
            self.state.field = FIELDS[value]
        elif key == "compare":
            self.state.comparison_mode = value
        elif key == "error":
            self.state.show_error = value
        elif key == "iso":
            self.state.show_isosurface = value
