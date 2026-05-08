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

## Apple Vision Pro CloudXR streaming setup

The `datacenter.dt.viewer_avp` variant streams the Boreas Operator viewport to an Apple Vision Pro headset over LAN via NVIDIA CloudXR. This section covers the pieces you need on the **server (Windows)**, the **client (Vision Pro via Macbook + Xcode)**, and the **network in between**.

### Server prerequisites (Windows)

NVIDIA's recommended spec (from `setup-network.html` / `requirements.html`):

- 2× NVIDIA RTX 6000 Ada 48 GB (Vision Pro) or 1× RTX 6000 Ada 48 GB (iPad)
- 128 GB RAM
- 16-core CPU (Threadripper Pro 5955WX class)
- Driver 553.62 or newer
- Kit SDK 107.3+

This Boreas fork is on **Kit 110.1.0** with `omni.kit.xr.cloudxr-6.0.5` (verified working as of May 2026). It is known to run on a single RTX 5080 Laptop (16 GB) at reduced frame rate / quality compared to the spec hardware. Treat NVIDIA's spec as a target, not a hard floor.

### Server step 1 — confirm the AVP variant builds with CloudXR enabled

```powershell
cd C:\Users\Ranga\omniverse\kit-app-template
.\repo.bat build
```

The build should resolve `omni.kit.xr.cloudxr` (currently 6.0.5) and the `omni.kit.xr.bundle.apple_vision_pro` extension (currently 109.0.0). If either fails, NVIDIA may have shipped a breaking change — check `source/apps/datacenter.dt.viewer_avp.kit` against NVIDIA's `setup-sdk.html`.

### Server step 2 — open the firewall ports

CloudXR uses one TCP port (connect channel) and several UDP ports (video, input, audio). Run **as Administrator** (the script is in this fork):

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\setup-avp-firewall.ps1
```

Removal:
```powershell
Get-NetFirewallRule -DisplayName "Boreas AVP CloudXR*" | Remove-NetFirewallRule
```

The rules are scoped to `kit.exe` so they don't permanently widen the firewall.

### Server step 3 — launch + start streaming

```powershell
_build\windows-x86_64\release\datacenter.dt.viewer_avp.bat
```

In the Kit window: **Window → AR** → select **Apple Vision Pro** profile → click **Start Streaming**. The Kit log will show the server-side IP + ports the client connects to.

### Client setup (Macbook + Xcode + Apple Developer account)

The Vision Pro client is NVIDIA's [`apple-configurator-sample`](https://github.com/NVIDIA-Omniverse/apple-configurator-sample). Required:

- Macbook with **Xcode 16.2+** on macOS Sonoma 14.4+
- **Paid Apple Developer enrollment** ($99/year) — free Apple IDs cannot deploy to physical Vision Pro
- An Apple Vision Pro on visionOS 2.0+

Build + sideload:

```bash
git clone git@github.com:NVIDIA-Omniverse/apple-configurator-sample.git
cd apple-configurator-sample
open Configurator.xcodeproj
```

In Xcode → **Configurator** target → **Signing & Capabilities**:
1. Set **Team** to your paid Apple Developer team
2. Change **Bundle Identifier** to a unique value (e.g., `com.<you>.boreas-avp-client`)
3. Plug in or pair the Vision Pro; pick it as the destination in **Product → Destination**
4. Press **Product → Run** (⌘R) — Xcode builds, signs, and installs
5. On the Vision Pro: **Settings → General → VPN & Device Management** → trust the developer certificate
6. The **Configurator** icon appears in the Vision Pro home screen

Pin to a known-good commit of the sample once you have it building, so a future NVIDIA update doesn't break your setup unannounced.

### Network requirements (the part that breaks demos)

NVIDIA's `setup-network.html` is unforgiving on this:

- Both server and client on the **same physical Wi-Fi network**, in the **same room with line of sight**
- **5 GHz or 6 GHz only** (channels 44 or 149 with 80 MHz preferred)
- **Recommended downstream:** 200 Mbps (minimum 100 Mbps); 1000 Mbps NIC on server
- **Latency:** 30 ms recommended, 100 ms maximum (pose-to-frame)
- **No public / guest / corporate Wi-Fi.** Guest networks (`SJSU_guest`, `eduroam`, hotel Wi-Fi) almost always have **client isolation** enabled — the firewall rules above mean nothing if the network blocks intra-client traffic. **Use a private LAN: home router, mobile hotspot, or travel router.**

Quick test from the laptop: `ping <vision-pro-ip>`. If ping doesn't work, no amount of firewall config will help — the network is isolating you.

### Verification checklist

| # | Check | Pass = |
|---|---|---|
| 1 | Server starts CloudXR | Kit log shows `[ext: omni.kit.xr.cloudxr-6.0.5+...] startup` |
| 2 | Server visible on LAN | `ping` between server and Vision Pro succeeds |
| 3 | First connection succeeds | Stereo render appears in the headset within 30 s of tapping Connect |
| 4 | Frame rate is acceptable | ≥ 60 Hz on RTX 5080 (NVIDIA target 90 Hz on spec hardware) |
| 5 | Round-trip latency tolerable | Pinch responds within ~150 ms (NVIDIA target 80 ms) |
| 6 | Boreas Operator panel still works | Server-side click on a sample question → agent runs → red marker visible in the streamed scene |
| 7 | Reconnect works | Disconnecting + reconnecting from the headset doesn't crash the server |

### Fallback: Simulated XR (no headset, no network)

If CloudXR isn't available (NVIDIA registry hiccup, network won't cooperate, hardware can't keep up), the same AVP `.kit` ships **Simulated XR**: open the AR panel → pick the Simulated XR profile → stereo render appears inside a desktop window. The operator agent + viewport still work; you just don't get the headset experience.

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
