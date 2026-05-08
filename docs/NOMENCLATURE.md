# Boreas Operator — Panel Nomenclature

Every label, control, and button on the **Boreas Operator** panel — what it means, what it does, and what's behind it. Use this doc to onboard new operators and to settle "what does that button do?" questions during the demo.

---

## Header strip

### Title — *"Boreas Operator"* (was: "Datacenter Digital Twin")
The brand name of this Kit application. Project codename Boreas (Greek god of the cold north wind). The thing you are looking at is the **operator console** for the Project Boreas datacenter Digital Twin.

### Subtitle — *"Datacenter operator console — Tier 1 + Tier 3 + Tier 4"* (was: "FNO vs U-Net …")
Names which tiers of NVIDIA's 5-tier Digital Twin framework this panel covers:
- **Tier 1 — Geometric** (the 3D OpenUSD scene + Cadence Reality DC bridge)
- **Tier 3 — Predictive** (the trained neural-operator surrogates serving the visualizations)
- **Tier 4 — Prescriptive** (the LLM operator agent, the "Ask the Twin" box)

Tier 2 (sensor → USD telemetry) and Tier 5 (autonomous closed-loop control) are future work.

> **Heads-up — only 2 of the 6 trained surrogates are visualized here.** The Boreas thesis trains six models (FNO, U-Net, PI-FNO, PI-U-Net, Transolver, POD+MLP). Only **FNO** and **U-Net** have USD geometry exports baked into `outputs/usd_omniverse/` — the other four are evaluated quantitatively in `results/` and `outputs/eval_report.json` but not rendered. This is a data-pipeline limitation, not a model-quality statement.

---

## Controls block

### "Room" dropdown — datacenter sample selector
Picks which **datacenter room configuration** is loaded into the viewport. Three rooms (0, 1, 2) are pre-rendered for the demo — each is one sample from the 192-room held-out test set of NVIDIA + Wistron's PhysicsNeMo-Datacenter-CFD dataset. Different rooms have different rack layouts, different cooling configurations, and different thermal/airflow patterns.

| Value | Meaning |
|---|---|
| Room 0 (config 0) | Baseline rack layout, all CRACs nominal |
| Room 1 (config 1) | Variant rack layout |
| Room 2 (config 2) | Variant rack layout |

Source files: `outputs/usd_omniverse/sample0_*.usdc`, `sample1_*.usdc`, `sample2_*.usdc`.

### "Surrogate" dropdown — neural-operator model
Picks which **trained ML surrogate model**'s prediction is displayed. The Boreas surrogates predict the full CFD field (temperature, velocity, pressure) from a datacenter geometry input, ~10,000× faster than the underlying OpenFOAM solve.

| Value | Params | T MAE | Inference latency |
|---|---:|---:|---:|
| FNO (28.3M params) | 28.3 M | 0.489 °C | 636 ms |
| U-Net (22.6M params) | 22.6 M | **0.205 °C** | **390 ms** |

The full six-model comparison from the thesis (PI-FNO, PI-U-Net, Transolver, POD+MLP) is in the **Analytics & Metrics** section below — those models have metrics but no USD viewport geometry yet.

### "Field" dropdown — CFD scalar/vector field
Which physical quantity is visualized in the viewport.

| Value | Unit | What it represents |
|---|---|---|
| Temperature (T) | °C | Air temperature at every grid point |
| Velocity Magnitude (U_magnitude) | m/s | Airflow speed at every grid point (vector magnitude) |
| Pressure (p) | Pa | Static pressure at every grid point |

---

## Checkboxes — display modifiers

These three checkboxes are **independent** (not single-select). Toggle any combination and click **Load Scene** to apply.

### "Side-by-side (GT left | Pred right)"
When **on**: viewport shows **Ground Truth on the left** and the **selected surrogate's Prediction on the right**, offset by 50 m on the Y axis. Lets the operator visually compare GT vs prediction in one view.
When **off**: only the prediction is loaded (no GT for comparison).
Default: **on**.

### "Show Error Map (3rd row)"
When **on**: adds a **third row offset** showing the per-voxel error (|prediction − GT|) as a magma colormap. Hot spots in the error map = where the surrogate is least accurate.
When **off**: only GT + Prediction (or just Prediction, if Side-by-side is off).
Default: **off**.

### "Isosurface Mode (T only)"
When **on**: renders the temperature field as an **isosurface mesh** (a 3D contour at a fixed °C threshold, rendered as solid geometry) instead of a colored point cloud.
When **off**: renders all fields as colored point clouds.
Default: **off**.

> **Why "T only"?** Isosurface USDs are pre-baked via marching-cubes only for temperature in the current asset pipeline (`generate_assets.py`). U_magnitude and p don't have isosurface USDs yet — toggling this with U or p selected falls back to point-cloud rendering. Future work: extend isosurfaces to all three fields.

---

## Action buttons

### "Load Scene" — primary CTA, green
Reads the current Room / Surrogate / Field / checkbox state and assembles the USD compose stage in the viewport:
- Side-by-side on → GT + Prediction offset by 50 m
- Error Map on → adds a third row at +100 m
- Isosurface Mode on (with T) → loads `*_T_iso.usdc` instead of `*_T.usdc`

After loading, the camera auto-frames the full scene. Use this **after every checkbox change or dropdown change** to apply the new selection.

### "GT Only" — secondary, gray
Loads **only the ground truth** for the current Room and Field, ignoring the surrogate / error / isosurface toggles. Useful for a clean reference view without prediction overlays.

---

## "Ask the Twin" — natural-language operator query

### The query StringField
Type any operator question — e.g., *"where is the hottest spot in room 1?"*, *"compare FNO vs U-Net pressure accuracy"*, *"recommend immediate action for the airflow distribution"*.

**Press Enter** or click **Ask** to submit. The agent (gpt-4o + 9 tools) reads the current view state, plans tool calls, and returns:
- A multi-paragraph operator-voice answer with ASHRAE references and recommendations
- A tool-call trace at the bottom (which tools were called, what arguments)
- A red marker on the viewport at the answer location, with the camera framed

### "Try" pill row
Click any pill to drop that example query into the input. Pre-baked queries that exercise different tool combinations.

---

## Analytics & Metrics

The collapsible **Analytics & Metrics** section below the action buttons shows aggregate numbers across the held-out 192-test-room set, **not** the current room.

### Sections inside

- **Verdict / Winner Banner** — one-line "U-Net wins N of M fields"
- **Per-field accuracy table** — FNO MAE / U-Net MAE / FNO R² / U-Net R² / Win, color-coded by quality band (R² ≥ 0.95 Excellent · ≥ 0.9 Good · ≥ 0.7 Fair · ≥ 0 Poor · negative)
- **Deployment** — params + GB10 inference latency + 5080 measured latency
- **Room range** — current-field GT min/max for the loaded room (sanity check)
- **Footer** — grid resolution + dataset citation

These metrics come from `results/{model}_metrics.json` (the canonical per-model evaluation files in the Boreas reference repo).

---

## What this panel does NOT do

For honesty during the demo, here's what's intentionally out of scope:

- **No live re-prediction.** All shown surrogate outputs are pre-baked. The agent reads numpy ground truth files for find_extremum / get_room_stats; it does not run the trained checkpoint on modified inputs (capacity-planning what-ifs are answered from current-state stats, not new inferences).
- **Only 2 of 6 surrogates have viewport assets.** PI-FNO, PI-U-Net, Transolver, POD+MLP show in the metrics tables but cannot be loaded into the 3D scene.
- **Isosurface only for temperature.** Pipeline limitation; see checkbox notes.
- **No multi-turn conversation.** Each query starts fresh; agent has no memory of prior questions.
- **No persistent operator session.** Settings reset on Kit relaunch.
- **No write operations to the underlying CFD or BMS.** The agent is read + visualize only; it cannot adjust a real cooling system. (Would be Tier 5 closed-loop control.)

---

## See also

- `BOREAS.md` — fork explainer + quickstart
- `RELATED-WORK.md` — academic + industry positioning
- Boreas project repo (archived): `irangareddy/298AB-dt-viewer@v1.0-thesis`
- This Kit app: `irangareddy/kit-app-template@v0.2.0-pre-demo`
