# Boreas Operator — Fork Notice

This repository is a fork of [NVIDIA-Omniverse/kit-app-template](https://github.com/NVIDIA-Omniverse/kit-app-template) that adds a custom Omniverse Kit application called **Boreas — Datacenter Operator Agent**, the Tier 1 visualization frontend of [Project Boreas](https://github.com/irangareddy/298AB-dt-viewer) (SJSU MSDA capstone, May 2026).

The upstream `kit-app-template` is unchanged in `templates/`, `tools/`, and the build system. All Boreas additions live under `source/`:

```
source/
├── apps/
│   ├── datacenter.dt.viewer.kit            ← desktop app (primary)
│   ├── datacenter.dt.viewer_streaming.kit  ← WebRTC headless companion
│   └── datacenter.dt.viewer_avp.kit        ← Apple Vision Pro CloudXR
└── extensions/
    └── datacenter.dt.analytics/            ← analytics panel + LLM agent
```

---

## What Boreas adds on top of `kit-app-template`

### A custom Kit Base Editor application — three deployment variants

All three apps share the same dependency graph and the same `datacenter.dt.analytics` extension. They differ only in delivery:

- **Desktop** — standard Kit window, the everyday demo path
- **WebRTC streaming** — headless Kit running on an RTX host, viewport streamed to a browser via Omniverse's standard streaming configuration
- **Apple Vision Pro** — CloudXR-served immersive variant for Vision Pro clients on the same LAN (see [apple-configurator-sample](https://github.com/NVIDIA-Omniverse/apple-configurator-sample))

App title across all three: **"Boreas — Datacenter Operator Agent"**.

### A custom extension that turns the viewer into an operator agent

`datacenter.dt.analytics` is a single-window Omni-UI extension with two interaction modes wired to the same underlying CFD data and the same surrogate USDs:

**Analytics mode** — load and switch between FNO / U-Net / ground-truth surrogate prediction USDs for three datacenter rooms; toggle visualization fields (T °C, U_magnitude m/s, p Pa); render side-by-side comparisons with R²-color-coded per-field metric panels.

**Agent mode** — natural-language operator query. OpenAI tool-calling loop (gpt-4o, max 10 reasoning steps) with **9 tools** that can both read the CFD state and *drive the viewport*:

| Tool | Effect |
|---|---|
| `describe_current_view` | Report active room, field, surrogate, mode |
| `set_room` | Switch active datacenter room (0, 1, 2) |
| `set_field` | Switch visualized field (T, U_magnitude, p) |
| `set_surrogate` | Pick FNO or U-Net for comparison |
| `find_extremum` | Find max / min of a field at full resolution |
| `get_room_stats` | Report min/max/mean/std for a field |
| `get_model_comparison` | Aggregate FNO vs U-Net metrics across 192 test rooms |
| `frame_camera` | Drop a red marker at a world point + frame the viewport |
| `load_scene` | Re-render the viewer after `set_*` calls so changes are visible |

The system prompt grounds the agent as a senior thermal engineer briefing the facility operator: cite numbers from tool calls, reference the ASHRAE A1 hot-aisle envelope (18-27 °C), recommend immediate / long-term / monitoring actions, and never invent numerical values.

A regex-only fallback parser handles queries when `OPENAI_API_KEY` is not set.

---

## Quickstart

### Build

Build everything (Kit kernel + dependencies + our apps):

```bash
./repo.sh build           # Linux / macOS
.\repo.bat build          # Windows
```

### Run

```bash
# Desktop (the demo)
_build/windows-x86_64/release/datacenter.dt.viewer.bat

# Streaming companion
_build/windows-x86_64/release/datacenter.dt.viewer_streaming.bat

# Apple Vision Pro CloudXR server layer
_build/windows-x86_64/release/datacenter.dt.viewer_avp.bat
```

### Configure the data root

The `datacenter.dt.analytics` extension reads its data from environment variables, so the same app works against any Boreas data layout:

```bash
export DT_PROJ_ROOT="/path/to/298AB-dt-viewer"
export DT_USD_DIR="$DT_PROJ_ROOT/outputs/usd_omniverse"
export DT_METRICS_DIR="$DT_PROJ_ROOT/outputs/omniverse_predictions"
export OPENAI_API_KEY="sk-..."     # optional — enables agent mode
```

Defaults assume the Boreas repo at `C:/Users/Ranga/298AB-dt-viewer`.

---

## Pulling NVIDIA upstream updates

Standard fork pattern. `origin` is this fork; `upstream` is NVIDIA:

```bash
git remote add upstream https://github.com/NVIDIA-Omniverse/kit-app-template.git
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

NVIDIA ships per-Kit-version branches (107.3, 108.0, 109.x, 110.0, 110.1.0, ...). Pin to a stable branch and merge from a newer one only deliberately. Boreas additions live under `source/`, fully isolated from `templates/` and `tools/` — merge conflicts with upstream are rare.

---

## Project Boreas — the bigger picture

This Kit app is **one chapter** of Project Boreas, the SJSU MSDA capstone. The full implementation (trained surrogate checkpoints, Streamlit demo, Tier 4 standalone LLM agent eval, paper drafts, golden-set benchmark) lives at:

> [github.com/irangareddy/298AB-dt-viewer](https://github.com/irangareddy/298AB-dt-viewer) — archived at `v1.0-thesis`

The five-tier datacenter Digital Twin framework Boreas implements:

```
Tier 4 — Prescriptive: Tool-grounded LLM operator (this app's Agent mode + 298AB-dt-viewer/tools/agent_*.py)
Tier 3 — Predictive:   Six neural-operator surrogates (U-Net 0.205 °C T MAE @ 390 ms inference)
Tier 2 — Descriptive:  Sensor → USD telemetry (future)
Tier 1 — Geometric:    OpenUSD scene + Boreas Operator Kit app (this fork) + Cadence Reality DC bridge
Reference data: NVIDIA + Wistron PhysicsNeMo-Datacenter-CFD, 960 simulations, 187 GB, Apache 2.0
```

---

## Attribution

Built on top of the open-source [NVIDIA Omniverse Kit App Template](https://github.com/NVIDIA-Omniverse/kit-app-template) (BSD-3-Clause). All upstream code, templates, build tooling, and documentation under `templates/`, `tools/`, `repo.toml`, `premake5.lua` (modulo a 3-line `define_app()` registration), `repo.sh`, `repo.bat`, and the original `README.md` belong to NVIDIA Corporation and remain under their license.

This fork's additions under `source/` and `BOREAS.md` are © Sai Ranga Reddy Nukala (SJSU MSDA capstone, May 2026).
