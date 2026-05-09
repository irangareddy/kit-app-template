# Boreas — Operator Agent + Apple Vision Pro Streaming

**Custom NVIDIA Omniverse Kit app — datacenter operator console with LLM agent and AVP CloudXR streaming.**

This document covers the kit-app-template fork only: the business case it serves, where it sits in the NVIDIA digital-twin stack, what the operator sees, what the agent does, how AVP streaming is set up, how to demo it, and how to know it's working. Surrogate model training and dataset preparation live in the separate research repo and are out of scope here.

---

## 1. What this is

A custom Omniverse Kit application that lets a datacenter operator:

- Load a pre-rendered USD scene of a datacenter room with a **surrogate-model temperature/velocity/pressure prediction** overlaid side-by-side with the ground-truth CFD result.
- Read a focused **metrics panel** that names the better surrogate for the chosen field, the inference latency, and the GT range for that room.
- **Ask an LLM agent** (GPT-4o) operator-style questions in natural language. The agent reads the loaded scene's metrics and viewport state, then drives the viewport (camera, marker) to point out hot spots, compliance issues, and recommendations.
- Optionally **stream the same viewport to an Apple Vision Pro headset** via NVIDIA CloudXR, so the operator can walk into the predicted scene in stereo.

Built on `NVIDIA-Omniverse/kit-app-template`. Forked at Kit SDK 110.0. Adds one Python extension and three `.kit` application variants.

---

## 2. The business case

Datacenters consume **1-2 % of global electricity** and the share is growing rapidly with AI workloads. **Cooling alone is 30-40 % of datacenter energy** — for a typical hyperscale facility that's tens of millions of dollars per year. Yet the standard tool for cooling design and "what-if" analysis is **OpenFOAM CFD simulation**, which takes **15-24 hours per scenario** on a powerful workstation. That's incompatible with the operator workflow:

- The **plant manager** needs to know "if I lose CRAC unit 3, do any racks exceed ASHRAE A1?" — and they need the answer in **seconds**, not days.
- The **design team** wants to evaluate dozens of layout variants per week. At 15 hours each, even a small parameter sweep takes a month.
- The **on-call engineer** investigating a thermal alarm has minutes, not hours.

**Surrogate neural-operator models** trained on CFD output close this gap. Boreas demonstrates this end-to-end: a U-Net surrogate produces a full-room T/U/p prediction in **390 ms** (~10,000× faster than CFD), with mean error **±0.205 °C** — well inside what an operator can act on. The Boreas Operator Kit app wraps that surrogate in a wearable interface so the plant manager can ask the agent *"where's the hottest rack?"* and get an immediate, ASHRAE-grounded answer projected in their headset.

**Validated real-world impact** (NVIDIA + Wistron's published deployment of the underlying dataset): **121,600 kWh/year energy savings per facility**, ~$15 k/year per facility at US commercial rates, with no infrastructure changes — purely from better-informed cooling decisions.

The Boreas demo is not an energy-savings calculator. It is the **operator-facing layer** that makes those savings achievable: it gives a human the surrogate's output in a form they can act on inside their workflow.

---

## 3. Where this fits in NVIDIA's 5-tier digital twin stack

NVIDIA's digital-twin reference architecture for industrial systems is organised as five tiers. Boreas implements four of them and uses NVIDIA's reference components at every layer:

| Tier | Role | NVIDIA component | What Boreas implements |
|---|---|---|---|
| **1 — Design** | Author the physical asset (CAD, room layout, equipment placement) | Cadence Reality DC Design Pro | Bridge proven: room STL → USD via `trimesh` + `usd-core`, ingested in Omniverse |
| **2 — Connectivity** | Stream live telemetry from physical sensors | Omniverse Connectors, Industrial AR | *Out of scope for this demo — natural next step* |
| **3 — Predictive engine** | Surrogate models that replace expensive CFD simulation | NVIDIA PhysicsNeMo | Six-model neural-operator benchmark; U-Net selected as production winner; results consumed by this app as USD + JSON |
| **4 — Operator console** | Visual interface for the human operator | NVIDIA Omniverse Kit | **Boreas Operator Kit app (this repo)** — panel, LLM agent, side-by-side comparison, metrics strips |
| **5 — Immersive interface** | Wearable AR/VR for the operator | NVIDIA CloudXR + OpenXR | **Boreas AVP variant** — Apple Vision Pro stereo streaming over LAN |

The Boreas defense covers Tiers 1, 3, 4, and 5 end-to-end. Tier 2 (live sensor connectivity) is the obvious next step beyond this work.

---

## 4. The three `.kit` variants

| File | Purpose | When |
|---|---|---|
| `source/apps/datacenter.dt.viewer.kit` | Desktop app | Default — operator drives the agent on a monitor |
| `source/apps/datacenter.dt.viewer_streaming.kit` | WebRTC livestream | Browser-side viewport streaming for remote demos |
| `source/apps/datacenter.dt.viewer_avp.kit` | Apple Vision Pro CloudXR server | Operator wears AVP headset, room streams in stereo |

All three depend on the same `datacenter.dt.analytics` Kit extension — the operator console code is shared.

---

## 5. The operator panel

Title: **Boreas Operator** (window title in the Kit app's right column). Three sections.

### 5.1 Controls

- **Room** dropdown — 3 sample rooms (Room 0/1/2 — see §10 for how to add more)
- **Surrogate** dropdown — FNO (28.3 M params) or U-Net (9.2 M params)
- **Field** dropdown — Temperature (°C) / Velocity Magnitude (m/s) / Pressure (Pa)
- **Side-by-side (GT left | Pred right)** checkbox — composes the two rooms 10 m apart in one stage
- **Show Error Map (3rd row)** checkbox — adds the per-cell |GT − Pred| error map at 20 m
- **Isosurface Mode (T only)** checkbox — replaces volume render with iso-surface for temperature
- **Load Scene** (green button) and **GT Only** (button)

### 5.2 Metrics

Three single-purpose strips designed for at-a-glance operator decisions, plus a collapsible full table for deeper questions.

- **Strip 1 — Best for {selected field}**: names U-Net or FNO as the winner with MAE in physical units, e.g. *"Best for Temperature: U-Net — 0.205 °C MAE — 2.4× more accurate than FNO"*
- **Strip 2 — Inference**: e.g. *"Inference: 390 ms (U-Net) — ~10,000× faster than the 15-hour OpenFOAM baseline"*
- **Strip 3 — This room — GT range for the selected field**: e.g. *"This room — GT Temperature range: [22.4, 41.8] °C"*
- **Collapsible: Full per-field comparison (FNO vs U-Net)** — full table with per-field MAE + R² + win-arrow for committee detail questions

Per-room metrics are read from JSON files at panel startup. No live model inference happens inside Kit — the inference cost was paid once when generating the metrics + USD prediction files.

### 5.3 Ask the Twin

- Free-text input
- **Try: ?sample questions?** dropdown — 5 prebuilt operator scenarios (see §7)
- **Ask** button with visible busy state during agent run
- Agent's reasoning trace + tool calls written back into the panel as it runs

---

## 6. The LLM agent

Implemented in `source/extensions/datacenter.dt.analytics/datacenter/dt/analytics/agent.py` and `prompts.py`.

| Property | Value |
|---|---|
| Model | `gpt-4o` (OpenAI tool-calling) |
| Max steps per query | 10 |
| Tools (9 total) | `read_metrics`, `read_field_at`, `read_field_extrema`, `read_panel_state`, `set_room`, `set_field`, `set_surrogate`, `place_marker_at`, `frame_camera_on_marker` |
| System prompt | ASHRAE A1 envelope (18-27 °C hot-aisle, 41 °C max), production-winner narrative, "operator agent assisting the human operator" framing |
| State sharing | Reads + writes the same `ViewState` the panel manipulates — agent's actions are visible in the panel and viewport simultaneously |

The agent's tool calls produce three operator-visible side effects:

1. **Camera reframes** — `frame_camera_on_marker` jumps the viewport so the marker is centered.
2. **Red marker prim appears** — `place_marker_at` writes a `/World/QueryMarker` Sphere at the world coords the agent computed.
3. **Panel controls update** — `set_room`, `set_field`, `set_surrogate` change the dropdowns, triggering metric strip rebuilds.

Multi-room queries are handled correctly: the agent passes a `room=` parameter to `read_*` tools so state doesn't leak between turns.

---

## 7. Operator use cases

The five sample queries in the **Try: ?sample questions?** dropdown are not arbitrary demo prompts — each maps to a real datacenter operator scenario the surrogate + agent must handle. Together they prove the system works for the workflows the committee will ask about.

### UC-1 — "What's the hottest point in this room?"

**Scenario**: A thermal alarm fires for Room 0. The on-call engineer needs to know within seconds where the hot spot is and how bad it is.

**What the agent does**:
- Calls `read_field_extrema(room=0, field="T")` — returns the (x, y, z) of the maximum predicted temperature and its value
- Calls `place_marker_at(x, y, z)` — drops a red sphere at that location
- Calls `frame_camera_on_marker()` — jumps the camera to center on the marker
- Replies with the location, the temperature in °C, and the margin to ASHRAE A1's 41 °C ceiling

**Why this matters**: collapses 15 hours of CFD + manual inspection into ~3 seconds.

### UC-2 — "Which room has the worst U-Net hot-spot prediction error?"

**Scenario**: Periodic surrogate-model audit. The engineering team wants to know which rooms the surrogate is least confident in, so they can prioritise re-training data.

**What the agent does**:
- Iterates `read_metrics(room=N)` for N in the configured rooms
- Compares the per-room U-Net T MAE
- Replies with the worst room and its MAE, plus a flag-for-re-training suggestion

**Why this matters**: proves multi-room reasoning works without state leak (this was the bug we fixed by adding the `room=` parameter to all read tools).

### UC-3 — "Is this room compliant with ASHRAE A1?"

**Scenario**: Regulatory or insurance audit. The facility must demonstrate every rack stays within ASHRAE A1 (18-27 °C inlet, 41 °C max).

**What the agent does**:
- Calls `read_field_extrema(room=0, field="T")` — gets max T
- Compares against the A1 thresholds carried in the system prompt
- Replies with PASS / FAIL and the worst margin

**Why this matters**: ASHRAE-grounded reasoning lives in the system prompt, not the tool schema. The agent's answer cites the specific envelope, not vague "looks OK."

### UC-4 — "Optimize: which CRAC unit should I dial up first?"

**Scenario**: Energy budget adjustment. The operator can boost cooling capacity in one of three CRAC zones. Which choice gives the most thermal headroom?

**What the agent does**:
- Iterates `read_metrics(room=N)` + `read_field_extrema(room=N, field="T")` across rooms
- Identifies which room is closest to the A1 ceiling (smallest margin)
- Recommends boosting cooling for that room first
- Calls `set_room(N)` so the operator immediately sees that room's data

**Why this matters**: drives the operator console state from agent reasoning. The agent isn't just answering text — it physically reframes the operator's view to focus their attention.

### UC-5 — "Compare FNO vs U-Net for this hot spot"

**Scenario**: Design-team review. Should the production deployment use FNO or U-Net? The operator wants the agent to walk them through the per-field tradeoff at the actual hot spot they're looking at.

**What the agent does**:
- Calls `read_metrics(room=0)` → gets both FNO and U-Net per-field MAE
- Calls `read_field_at(room=0, x, y, z)` for both surrogates at the hot-spot coords
- Compares predicted T values and reports the MAE for each
- Replies with the recommendation backed by numbers

**Why this matters**: justifies the U-Net production-winner choice with evidence the operator can verify, not assertion.

---

## 8. Apple Vision Pro CloudXR streaming

Added on `feat/avp-streaming` → merged to `main` → tagged `v0.3.0-avp`.

### 8.1 What it does

The AVP variant runs the same Kit app but adds NVIDIA CloudXR 6.0 as an OpenXR runtime, so the viewport is stereo-streamed to an Apple Vision Pro headset on the same Wi-Fi LAN. The operator wears the headset, sees the datacenter room, and the agent's actions (camera framing, marker placement) are visible in stereo in real-time.

### 8.2 The `.kit` additions vs the desktop variant

```toml
[dependencies]
"datacenter.dt.viewer" = {}                      # the desktop app
"omni.kit.xr.bundle.apple_vision_pro" = {}       # AVP XR profile + Simulated XR
"omni.kit.xr.cloudxr" = {}                       # CloudXR transport

[settings]
xr.openxr.preferNVOpaqueDataChannel = true       # NVIDIA-required for AVP CloudXR
rtx.verifyDriverVersion.enabled = false
```

### 8.3 Server hardware reality

| Spec | NVIDIA recommends | What we have | Result |
|---|---|---|---|
| GPU | 2× RTX 6000 Ada (48 GB each) | 1× RTX 5080 Laptop (16 GB) | works with extra buffering |
| RAM | 128 GB | 64 GB | OK |
| CPU | Threadripper Pro 16-core | Core Ultra 9 24-core | OK |

Below recommended spec but functional. Frame rate ~60-72 Hz instead of 90 Hz target. Latency ~100-150 ms instead of 80 ms target. Acceptable for a defense demo, not production.

### 8.4 Network setup — the single biggest blocker

The single biggest blocker for first connection is **firewall + network category**, not Kit configuration. Two PowerShell scripts ship in `scripts/`:

- `scripts/setup-avp-firewall.ps1` — opens the four CloudXR port families inbound, scoped to `kit.exe`
- `scripts/avp-network-fix.ps1` — combines the firewall rules **plus** reclassifies the active Wi-Fi as Private. Use this for first time on a new network.

Required firewall rules (all inbound, scoped to `kit.exe`):

| Port | Protocol | Purpose |
|---|---|---|
| 48010 | TCP | CloudXR connect channel |
| 47998, 48005, 48008, 48012 | UDP | Video |
| 47999 | UDP | Input |
| 48000 | UDP | Audio |

Wi-Fi requirements:

- 5 GHz or 6 GHz (not 2.4 GHz — explicit NVIDIA doc requirement)
- Network category **Private** (Public is more restrictive on inbound)
- AP client isolation **off** (corp/guest networks usually have this on; it silently breaks the demo with no clear log signal)

If everything looks correct but TCP 48010 is unreachable from another LAN device, disable Windows Firewall as a temporary diagnostic to confirm: `Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False` (re-enable after the demo).

### 8.5 Client app — apple-configurator-sample

Built and sideloaded from `NVIDIA-Omniverse/apple-configurator-sample` on a Macbook with Xcode 16.2 + a paid Apple Developer account. Bundle ID: `com.irangareddy.boreas-avp-client`.

**Critical version match**: the client must be built against **CloudXR 6.x** SDK. Older clients (5.x, 4.1) silently fail handshake against a 6.0 server with the misleading "connection unsuccessful" error and no incoming-connection log entry on the server.

### 8.6 GT ↔ Pred spacing

`SIDE_BY_SIDE_OFFSET` in `config.py` controls the center-to-center distance between Ground Truth and Prediction rooms when side-by-side mode is enabled. Room is ~3.84 m wide along this axis.

| Value | Visible gap | When |
|---|---|---|
| 50 m | 46 m | Original — fine for desktop bird's-eye, too wide in headset |
| 6 m | 2 m | Too close to compare |
| **10 m** | **6 m** | **Current** — comfortable in headset, two rooms still in field of view |

### 8.7 Z-up vs Y-up — known consideration

The source USD predictions are Z-up (CFD convention); Omniverse XR streams in Y-up. Without compensation the streamed room appears tilted/floating in the headset. For this demo: select `/World` in the Stage panel and add `rotateXYZ = (-90, 0, 0)` plus `translateY = -1.2` in the Property panel before going live. A permanent fix (re-export the USDs as Y-up upstream) is future v0.4 work.

---

## 9. Evaluation — how we know it works

Three levels of evaluation, one per tier of the stack the demo touches.

### 9.1 Surrogate accuracy (Tier 3)

Every room's metrics JSON contains both surrogates' per-field MAE in physical units. The metrics panel exposes this so the operator and the committee can verify the prediction is grounded in numbers, not vibes:

| Field | U-Net MAE | FNO MAE | Winner |
|---|---|---|---|
| Temperature | **0.205 °C** | 0.489 °C | U-Net (2.4×) |
| Velocity Magnitude | **0.142 m/s** | 0.226 m/s | U-Net (1.6×) |
| Pressure | **0.083 Pa** | 0.119 Pa | U-Net (1.4×) |

For the full per-component breakdown (Ux, Uy, Uz) and R² scores, expand the **Full per-field comparison (FNO vs U-Net)** collapsible in the metrics panel.

The "U-Net is the production winner" claim drives the panel's defaults, the agent's recommendations, and the strip-1 framing.

### 9.2 Agent correctness (Tier 4)

Each of the 5 sample use cases (§7) was tested end-to-end across all 3 rooms. Acceptance criteria:

| Check | Pass = |
|---|---|
| Agent calls the right tools in the right order | All 5 queries complete within `AGENT_MAX_STEPS = 10` |
| Marker lands at the actual extremum | Marker world coords match `read_field_extrema()` output to within 1 grid cell (4 cm) |
| Numbers in the agent's reply match the metrics JSON | Spot-check 3 queries × 3 rooms = 9 manual verifications |
| ASHRAE compliance verdict is correct | Ground-truth A1 envelope (18-27 °C inlet, 41 °C max); agent's PASS/FAIL matches |
| Multi-room queries don't leak state | UC-2 and UC-4 return different answers when re-run for different rooms |

UC-2 and UC-4 are the canary tests — they failed before the `room=` parameter was added to `read_*` tools, and pass now. That fix is documented in the agent module.

### 9.3 Streaming acceptability (Tier 5)

For the AVP demo, on the below-spec RTX 5080 laptop:

| Metric | NVIDIA target | Observed | Acceptable? |
|---|---|---|---|
| Frame rate | 90 Hz | 60-72 Hz | yes (below-spec hardware) |
| Round-trip latency | 80 ms | 100-150 ms | yes |
| Time to first frame after Connect | < 30 s | ~10 s | yes |
| Reconnect after disconnect | succeeds | succeeds | yes |
| Side-by-side rooms in field of view at 1:1 scale | both visible | both visible (10 m offset) | yes |

If any of these regress on demo day, the desktop variant is the fallback; both variants are first-class.

---

## 10. Adding more rooms

The shipped app has **3 rooms** (Room 0, 1, 2). The dropdown is driven by `SAMPLES = [0, 1, 2]` in `config.py`. Each room needs both a set of USD prediction files and a metrics JSON; without either, the panel will say *"No metrics on disk for this room"* and the scene loader will log `ABORT — missing GT or Prediction file`.

### 10.1 Where the data lives

```python
# source/extensions/datacenter.dt.analytics/datacenter/dt/analytics/config.py
PROJ_ROOT    = ~/298AB-dt-viewer            # override with $DT_PROJ_ROOT env var
USD_DIR      = $PROJ_ROOT/outputs/usd_omniverse           # override with $DT_USD_DIR
METRICS_DIR  = $PROJ_ROOT/outputs/omniverse_predictions   # override with $DT_METRICS_DIR
```

For each room `N`, the panel expects:

| Path | Files |
|---|---|
| `$USD_DIR/sample{N}_ground_truth_{T,U_magnitude,p}.usdc` | 3 GT volumes |
| `$USD_DIR/sample{N}_{fno_pred,unet_pred}_{T,U_magnitude,p}.usdc` | 6 prediction volumes |
| `$USD_DIR/sample{N}_{fno_pred,unet_pred}_error_{T,U_magnitude,p}.usdc` | 6 error maps (used when "Show Error Map" is on) |
| `$USD_DIR/sample{N}_{fno_pred,unet_pred}_T_iso.usdc` | 2 temperature iso-surfaces (used when "Isosurface Mode" is on) |
| `$METRICS_DIR/sample{N}_metrics.json` | per-field MAE + R² + GT range + inference latency |

### 10.2 Adding rooms 3, 4, …

Three steps, run from the **research repo (298AB)**, not this one:

1. **Have the raw test data** in `$DT_PROJ_ROOT/test_data/` for the new sample IDs (these come from the PhysicsNeMo dataset's test split).
2. **Run inference + export** for each new sample with both surrogates. The exporter writes the `.usdc` files + a `_metrics.json` into the directories above. Entry point: `generate_assets.generate(...)` from `datacenter.dt.analytics/generate_assets.py` — invoke it offline from a notebook in the 298AB repo, or it auto-runs the first time the panel is opened on a fresh install (`_ensure_generated()`).
3. **Edit two lines** in `config.py`:
   ```python
   SAMPLES       = [0, 1, 2, 3, 4]
   SAMPLE_LABELS = {0: "Room 0 (config 0)", 1: "Room 1 (config 1)", 2: "Room 2 (config 2)",
                    3: "Room 3 (config 3)", 4: "Room 4 (config 4)"}
   ```
   Save → the dropdown picks the new entries up on the next panel rebuild (Kit hot-reloads the extension on file change).

### 10.3 What does NOT live in this repo

The **USD prediction files and metrics JSONs are not in `kit-app-template`** — they live in `~/298AB-dt-viewer/outputs/...`. This is intentional: kit-app-template is a public fork of NVIDIA's template and stays application-code-only; the surrogate model outputs are research artifacts and stay in the research repo. The `DT_PROJ_ROOT` / `DT_USD_DIR` / `DT_METRICS_DIR` env vars decouple the two.

For demo-day reproducibility on a fresh machine: clone this repo, set `DT_PROJ_ROOT` to wherever the research repo's `outputs/` directory is, then build + launch.

---

## 11. Repository layout

```
kit-app-template/
├── BOREAS.md                                  ← fork explainer + AVP setup section
├── docs/
│   ├── NOMENCLATURE.md                        ← UI vocabulary + tooltip text
│   ├── RELATED-WORK.md                        ← positioning vs prior Kit-app work
│   └── CAPSTONE-DOSSIER.md                    ← this file
├── scripts/
│   ├── avp-network-fix.ps1                    ← one-shot Wi-Fi + firewall
│   └── setup-avp-firewall.ps1                 ← firewall only
├── source/
│   ├── apps/
│   │   ├── datacenter.dt.viewer.kit           ← desktop variant
│   │   ├── datacenter.dt.viewer_streaming.kit ← WebRTC variant
│   │   └── datacenter.dt.viewer_avp.kit       ← AVP CloudXR variant
│   └── extensions/datacenter.dt.analytics/
│       └── datacenter/dt/analytics/
│           ├── extension.py                   ← main panel + scene loaders
│           ├── agent.py                       ← LLM tool-calling loop
│           ├── prompts.py                     ← system prompt + 9 tool schemas
│           ├── view_state.py                  ← ViewState dataclass
│           ├── theme.py                       ← Color, Font, helpers
│           ├── config.py                      ← paths + SIDE_BY_SIDE_OFFSET
│           ├── denormalize.py                 ← T/U/p physical-unit conversion
│           ├── log.py                         ← logger
│           └── generate_assets.py             ← dataset → USD pipeline glue
└── _build/windows-x86_64/release/
    ├── datacenter.dt.viewer.bat               ← desktop launcher
    ├── datacenter.dt.viewer_streaming.bat     ← WebRTC launcher
    └── datacenter.dt.viewer_avp.bat           ← AVP launcher
```

---

## 12. Demo flow — May 9 dry-run

### 12.1 Desktop variant (primary)

1. **Launch**: `_build\windows-x86_64\release\datacenter.dt.viewer.bat`
2. Wait for Kit window (15-30 s on warm shader cache, longer on first launch)
3. **Window → Boreas Operator** if panel not visible (it is by default)
4. Select **Room 0**, **U-Net (9.2 M params)**, **Temperature**
5. Click **Load Scene** — GT (left) and U-Net prediction (right) appear 10 m apart
6. Read the metric strips aloud:
   - *"Best for Temperature: U-Net — 0.205 °C MAE — 2.4× more accurate than FNO"*
   - *"Inference: 390 ms (U-Net) — ~10,000× faster than the OpenFOAM baseline"*
   - *"This room — GT Temperature range: [22.4, 41.8] °C"*
7. **Ask the Twin** → pick **UC-1** *"What's the hottest point in this room?"* — agent reframes camera + drops red marker
8. **UC-3** *"Is this room compliant with ASHRAE A1?"* — proves grounded reasoning
9. **UC-4** *"Optimize: which CRAC unit should I dial up first?"* — proves multi-room reasoning + driving panel state from agent

### 12.2 AVP variant (secondary, optional headset demo)

**First-time setup** (one-time per machine):

- Run `scripts\avp-network-fix.ps1` (right-click → Run with PowerShell, accept UAC) — sets Wi-Fi private + adds 4 firewall rules

**Per-session**:

1. Launch `_build\windows-x86_64\release\datacenter.dt.viewer_avp.bat`
2. Wait for Kit window
3. **XR tab** in panel column → Output Plugin = **OpenXR**, Runtime = **CloudXR 6.0 (Native)**
4. Click **Start AR** — viewport status: *"AR profile is active"*; log: *"Waiting for connection"*
5. (Optional Z-up tweak) **Stage panel** → select `/World` → **Property panel** → Transform → **Rotate X = -90**, **Translate Y = -1.2**
6. Put on Vision Pro → open **Configurator** app → **Connect** → IP `192.168.0.185`
7. Within ~10 s: stereo room appears in headset
8. Click sample question on the laptop side; the operator in the headset sees the marker land in stereo

### 12.3 Fallback if AVP fails on demo day

Skip step 12.2 entirely. Desktop variant carries the demo. Mention "Vision Pro variant exists, here's the proof" and show `source/apps/datacenter.dt.viewer_avp.kit`. The committee will accept the technology as proven.

---

## 13. Build & launch commands

### 13.1 Build

```bash
cd C:\Users\Ranga\omniverse\kit-app-template
.\repo.bat build
```

First build takes 15-30 min (downloads extension cache). Incremental builds are seconds.

### 13.2 First-run network setup (one-time per machine)

```powershell
# Right-click → Run with PowerShell, accept UAC
C:\Users\Ranga\omniverse\kit-app-template\scripts\avp-network-fix.ps1
```

If the active Wi-Fi SSID differs from `"ADS Lab"`, edit the `$WIFI_NAME` variable at the top of the script first.

### 13.3 Sanity-check before headset connect

```powershell
# Are the firewall rules in place?
Get-NetFirewallRule -DisplayName "Boreas AVP*" | Format-Table -AutoSize

# Is Kit actually listening on the CloudXR port?
Get-NetTCPConnection -LocalPort 48010 -State Listen
```

### 13.4 Verify reachability from another LAN device

```bash
# From Macbook or any laptop on the same Wi-Fi
ping -c 3 192.168.0.185         # ICMP — should always succeed
nc -zv 192.168.0.185 48010      # success = server reachable from LAN
```

If `nc` times out but ping succeeds, the issue is firewall scope or AP client isolation.

---

## 14. Troubleshooting catalog

| Symptom | Cause | Fix |
|---|---|---|
| "Connection attempt unsuccessful" on Vision Pro | TCP 48010 not reachable from LAN | Run `avp-network-fix.ps1` as admin; reclassifies Wi-Fi to Private and adds firewall rules |
| Same as above, but firewall rules already in place | Windows still drops inbound on certain interfaces | Disable Windows Firewall temporarily: `Set-NetFirewallProfile -All -Enabled False` |
| Configurator connects but server stays "Waiting" | CloudXR client SDK version mismatch | Pull latest `apple-configurator-sample`, rebuild against CloudXR 6.x |
| Streamed room appears tilted/floating | Z-up source vs Y-up XR convention | Manually rotate `/World` in Stage panel: `rotateXYZ = (-90, 0, 0)` |
| AR panel says "Running SimulatedXR" | User accidentally switched runtime | AR panel → Output Plugin = OpenXR, Runtime = **CloudXR 6.0 (Native)** |
| Server log shows `device-profile set to 'auto-webrtc'` | User picked CloudXR 6.0 (WebRTC) instead of (Native) | Change runtime back to **CloudXR 6.0 (Native)** |
| Kit hangs on first launch | RTX shader compilation | Wait — first launch can take 5-10 min |
| Scene loads but viewport is empty | Camera not framed on scene | Press **F** in viewport, or **Edit → Frame Selected** with `/World` selected |
| "Load Scene" appears to do nothing in headset | AR streaming was stopped between sessions | Check `Get-NetTCPConnection -LocalPort 48010 -State Listen` — if empty, click Start AR again |
| Two `kit.exe` processes after stopping | Stale process from previous launch | `Stop-Process -Name kit -Force`, then relaunch |
| Agent gives wrong answer for room N | UC-2 / UC-4 multi-room state leak | Ensure the `room=` parameter is in the agent's tool calls (fixed in current build) |

---

## 15. Tags and milestones

| Tag | Commit | Meaning |
|---|---|---|
| `v0.2.0-pre-demo` | `153ddce` | Desktop demo ready — refactor (1182 → 833 lines), 8 sibling modules, agent + metrics polish, NOMENCLATURE.md + RELATED-WORK.md |
| `v0.3.0-avp` | `6dbd5c0` | AVP CloudXR streaming verified end-to-end — Y-up wrapper (later reverted), network setup scripts, BOREAS.md AVP section |

Demo-day adjustments after `v0.3.0-avp`:
- Y-up wrapper from `5af63af` reverted in `c8e67f2`
- 6 m offset from `962bc54` reverted in `47b9aa2`
- Final 10 m offset shipped in `82bcb15`
- This dossier shipped in `c8fc1f3`

---

## 16. Quick-reference key commands

```bash
# Build
cd C:\Users\Ranga\omniverse\kit-app-template && .\repo.bat build

# Launch desktop demo
_build\windows-x86_64\release\datacenter.dt.viewer.bat

# Launch AVP (Vision Pro server)
_build\windows-x86_64\release\datacenter.dt.viewer_avp.bat

# Network setup (first time on a new Wi-Fi)
# Right-click → Run with PowerShell
scripts\avp-network-fix.ps1

# Sanity-check before headset connect
Get-NetTCPConnection -LocalPort 48010 -State Listen   # should show kit.exe owning 48010
Get-NetFirewallRule -DisplayName "Boreas AVP*"        # should show 4 rules, all Enabled=True

# Cleanup
Stop-Process -Name kit -Force                          # kill any stale Kit processes
```

---

*Last updated: end of v0.3.0-avp + demo-day tuning, May 8, 2026.*
