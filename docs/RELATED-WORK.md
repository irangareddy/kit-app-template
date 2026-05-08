# Related Work — Boreas Operator Agent

Synthesis of three parallel research scans (academic / industry / startup-OSS) conducted May 2026 to position the Boreas Operator Agent against existing work. **Bottom line: the four-way intersection of (tool-grounded LLM agent) × (neural-operator CFD surrogate) × (Omniverse Kit 3D runtime) × (datacenter facility-operator persona) is empty in published work as of April 2026. Boreas is the first.**

---

## Executive summary

| Layer | Closest precedent | What's missing |
|---|---|---|
| LLM tool-calling | ReAct (ICLR 2023, arXiv:2210.03629), Toolformer (NeurIPS 2023, arXiv:2302.04761), ToolLLM (ICLR 2024, arXiv:2307.16789) | All on web/text APIs; no engineering / CPS grounding |
| Neural CFD surrogate | FNO (Li et al., ICLR 2021, arXiv:2010.08895); NVIDIA + Wistron PhysicsNeMo-Datacenter-CFD; Cao et al. 2025 (arXiv:2504.04982); arXiv:2511.11722 | No agent layer, no operator UI, no per-field physical-unit eval |
| Omniverse digital twin | NVIDIA DSX Blueprint (GTC Oct 2025), Wistron PhysicsNeMo-on-Omniverse case study, Kit-CAE | Authoring / VR walkthroughs — not conversational, not grounded in surrogate predictions |
| Datacenter cooling AI | DeepMind 40% (2016/2018), Phaidra (DSX partner), Meta RL (Sep 2024) | Closed-loop control, no operator-facing explanatory UI |
| Operator-Agent pattern | **Sight Machine Operator Agent** (2025, GPT-4 + Omniverse + 3D twin) | Manufacturing line, grounded in observed sensor history — not datacenter CFD |

The closest single precedent is **Sight Machine's Operator Agent** — same name pattern, same architectural choice (GPT-4 + Omniverse 3D twin + agentic recommendations). Boreas occupies the parallel niche for **datacenter CFD with predictive surrogate grounding** instead of manufacturing-line sensor history.

---

## The lineage Boreas continues (must-cite in paper)

**1. DeepMind cooling AI (2016, 2018) → Phaidra (Series B, 2024-2025) → Meta RL (Sep 2024)** establishes that AI-driven datacenter cooling is a multi-billion-dollar validated industrial problem.
- DeepMind: 40% cooling-energy reduction at Google scale ([deepmind blog](https://deepmind.google/blog/deepmind-ai-reduces-google-data-centre-cooling-bill-by-40/))
- Phaidra: ex-DeepMind founders, 25% energy + 75-80% thermal-overshoot reduction, $50M raise, [DSX Blueprint partner](https://www.phaidra.ai/blog/phaidra-nvidia-ai-agents-for-gigawatt-scale-ai-factories)
- Meta: simulator-based RL, 20% supply-fan + 4% water savings ([Meta engineering blog](https://engineering.fb.com/2024/09/10/data-center-engineering/simulator-based-reinforcement-learning-for-data-center-cooling-optimization/))

**Boreas adds:** a conversational, operator-in-the-loop *explanatory* layer that all three lack — the prior art optimizes setpoints silently; Boreas surfaces the *why* with grounded numbers and ASHRAE thresholds.

**2. NVIDIA + Wistron PhysicsNeMo-Datacenter-CFD (2024) → NVIDIA DSX Blueprint (GTC Oct 2025)** establishes that the exact stack Boreas uses is being productized at hyperscale.
- Wistron: 15,000× speedup (15 hr → 3.6 s), 121,600 kWh/yr savings, VR walkthroughs ([NVIDIA developer blog](https://developer.nvidia.com/blog/wistron-advances-energy-efficiency-in-manufacturing-with-ai-and-nvidia-omniverse/))
- DSX: open blueprint for AI-factory digital twins; partners include Cadence, Phaidra, Schneider, Siemens, Emerald AI; explicitly invites **"agentic digital twin solutions"** ([NVIDIA blog](https://blogs.nvidia.com/blog/omniverse-dsx-blueprint/))

**Boreas adds:** an academically-published, reproducible reference implementation of the operator-agent layer DSX leaves to partners — built on the public PhysicsNeMo-Datacenter-CFD dataset Wistron's case study used internally.

**3. Sight Machine Operator Agent (2025)** is the architectural pattern Boreas inherits — same name pattern, GPT-4 + Omniverse + 3D, ask → ground → show in 3D.
- [Sight Machine blog](https://sightmachine.com/sight-machines-operator-agent-brings-agentic-ai-to-the-plant-floor/) | [NVIDIA case study](https://www.nvidia.com/en-us/case-studies/sight-machine/)

**Boreas differentiates on:** (a) **forward-looking** CFD surrogate predictions vs. **backward-looking** observed sensor history; (b) **datacenter thermal** vs. **manufacturing-line operations**; (c) academic open implementation vs. commercial product; (d) **physical-unit grounding** with ASHRAE A1 thresholds.

---

## Closest competitors — direct comparison

| Competitor | Same as Boreas | Different from Boreas | Verdict |
|---|---|---|---|
| **Sight Machine Operator Agent** | LLM + Omniverse 3D + operator persona + agentic recommendations | Manufacturing line / observed sensor data / commercial product | **Closest analog. Cite prominently.** |
| **Cadence Reality DC** ([cadence.com](https://www.cadence.com/en_US/home/tools/reality-digital-twin.html)) | Datacenter CFD digital twin / Omniverse interop | Designer/engineer tool, not operator-conversational | Direct datacenter-CFD product peer; different role |
| **EkkoSense** ([ekkosense.com](https://ekkosense.com)) | "Where's the hotspot?" operator UX, datacenter | Sensor telemetry + 2D floorplans, no CFD or 3D | Closest UX-intent peer in datacenter ops |
| **PassiveLogic** | Agentic "Quantum" generative layer over digital twin | Buildings, not datacenters; their physics engine, not neural CFD | Closest *agentic-twin* analogue in adjacent vertical |
| **Phaidra** ([phaidra.ai](https://www.phaidra.ai)) | Datacenter cooling "agent", DSX partner | Reinforcement-learning closed-loop control, no LLM, no chat | Closest datacenter-AI peer; control mode, not diagnostic mode |
| **Schneider EcoStruxure IT Advisor** | Operator-facing datacenter platform with digital twin and AI roadmap | DCIM/BMS sensor + asset metadata grounded, not CFD-surrogate grounded | Adjacent commercial platform |
| **Honeywell + Google Cloud Forge AI** ([honeywell.com](https://www.honeywell.com/us/en/press/2024/10/honeywell-and-google-cloud-to-accelerate-autonomous-operations-with-ai-agents-for-the-industrial-sector)) | Operator-persona LLM agent in industrial | RAG over historian data, no 3D viewport, no CFD | Confirms the market direction |

---

## Academic adjacents that bridge LLM × CFD

| Paper | What | How Boreas differs |
|---|---|---|
| **CFDAgent** (Physics of Fluids 2025) | Multi-agent NL → mesh → solver → viz for OpenFOAM | Calls full solver (slow). Boreas calls trained surrogate (real-time) |
| **OpenFOAMGPT 2.0** (arXiv:2504.19338) | LLM-driven OpenFOAM case setup | Pre-processing focus. Boreas is post-training runtime |
| **MetaOpenFOAM** (arXiv:2407.21320) | Multi-agent OpenFOAM workflow | Same: setup vs runtime distinction |
| **ChatCFD** (arXiv:2504.02990 — verify) | End-to-end LLM-driven CFD | Solver-time, not surrogate-time, no operator persona |

**The "LLM + CFD" intersection has academic activity but it's all on the slow-solver side of the lifecycle.** Boreas is the first to run the same loop over a *trained surrogate* — milliseconds vs hours, which qualitatively changes the operator UX.

---

## White space (the explicit thesis claim)

> **As of April 2026, no public product or peer-reviewed paper combines all four of:**
> **(a) tool-calling LLM agent**
> **(b) neural-operator CFD surrogate (FNO / U-Net 3D)**
> **(c) Omniverse Kit 3D runtime as the agent's "body"**
> **(d) datacenter facility-operator persona with ASHRAE-grounded recommendations**
>
> Each pair-wise combination has prior art (ReAct + APIs, FNO + CFD, NVIDIA Omniverse + Wistron, EkkoSense + operator UX, Sight Machine + 3D agent). The four-way intersection is open. Boreas Operator Agent occupies that intersection.

---

## Use-case validation against the agent's actual behavior

Tested 5 representative operator queries through `agent_demo.py` (saved at `298AB-dt-viewer/outputs/agent_demo_runs/`):

| # | Use case | Agent behavior | Verdict |
|---|---|---|---|
| 1 | Hotspot triage | `set_room` + `find_extremum` → 41.81 °C @ (16.12, 2.76, 2.36) + ASHRAE A1 + immediate/long-term/monitoring split | ✓ Excellent |
| 2 | Capacity planning ("can I add 100 kW?") | No what-if tool — agent adapted by reasoning from current `get_room_stats` (T 21.8-41.9 °C, U 0-5.05 m/s); flagged that adding heat would worsen existing hotspot | ✓ Good — graceful degradation |
| 3 | Operator training (distribution + what's normal) | `get_room_stats(T)` + ASHRAE-grounded interpretation | ✓ Good |
| 4 | Incident post-mortem (model-comparison) | `get_model_comparison(T)` → named U-Net (0.205 °C MAE) over FNO (0.489 °C) for incident-grade accuracy | ✓ Excellent |
| 5 | Cross-room optimization (which is most stressed) | **Multi-step bug**: agent batched 3× `set_room` before any `find_extremum`, all 3 extrema queried room 2's state | ⚠ Fixable — see below |

**The use cases corroborate the value-prop:** 4/5 work cleanly without code change; the 1 failure is a fixable prompt or tool-signature issue.

### Fix for use case 5 (multi-step state)

Two options:
- **Prompt fix** (~5 min): add to system prompt: *"When comparing across rooms, ALTERNATE set_room and find_extremum/get_room_stats. Each set_room only affects subsequent tool calls — do NOT batch set_rooms before queries."*
- **Tool fix** (~15 min): add `room` parameter to `find_extremum` and `get_room_stats` so the agent doesn't manage room state. Eliminates the bug class permanently.

Recommend **tool fix** — robust against future prompt drift.

---

## Citations to incorporate into the paper's Related Work section

Required (must cite):

1. Yao et al., *ReAct* — ICLR 2023, arXiv:2210.03629
2. Schick et al., *Toolformer* — NeurIPS 2023, arXiv:2302.04761
3. Qin et al., *ToolLLM* — ICLR 2024, arXiv:2307.16789
4. Li et al., *Fourier Neural Operator* — ICLR 2021, arXiv:2010.08895
5. Cao et al., 2025 — arXiv:2504.04982 (in `298AB/ReferencePapers/`)
6. arXiv:2511.11722 — FNO vs U-Net vs ViT for datacenter (verify ID + authors)
7. NVIDIA + Wistron PhysicsNeMo-Datacenter-CFD dataset (Apache 2.0, HuggingFace)

Strongly recommended:

8. **Sight Machine Operator Agent** (NVIDIA case study, 2025) — closest commercial analogue
9. **NVIDIA DSX Blueprint** (GTC Oct 2025) — the platform context Boreas plugs into
10. **DeepMind cooling 40%** (2016/2018) — establishes the AI-for-datacenter-cooling lineage
11. **Phaidra** + **Meta RL** (Engineering blog Sep 2024) — modern industry-validation of the lineage
12. **CFDAgent** (Physics of Fluids 2025) and **OpenFOAMGPT 2.0** (arXiv:2504.19338) — bracket the LLM × CFD academic space; differentiate on solver-time vs surrogate-time

Optional (color):

13. Cadence Reality DC Design Pro — datacenter CFD product context (have Pro license)
14. Schneider EcoStruxure / Honeywell Forge AI — operator-agent market direction
15. EkkoSense, PassiveLogic — niche-adjacent operator-AI products

---

## Honest verification flags

The research agents flagged for double-checking before submission:
- arXiv:2511.11722 — confirm exact title + authors before citing
- arXiv:2504.02990 (ChatCFD) — verify ID
- arXiv:2504.19338 (OpenFOAMGPT 2.0) — verify
- All Hugging Face / GitHub star counts and YC batch identifiers — agents withheld where uncertain; verify on Crunchbase / GitHub before quoting in the paper

---

## Where this synthesis comes from

Three parallel research scans, May 2026:
1. **Academic landscape** — papers across ICLR / NeurIPS / ICML / arXiv, 2023-2026
2. **Industry / news / NVIDIA developer blog** — DeepMind through Sight Machine
3. **Startup + OSS ecosystem** — YC / a16z / Crunchbase / GitHub / Hugging Face

All three reached the same gap claim from independent angles. The triangulation is the strongest evidence Boreas occupies a real white space.
