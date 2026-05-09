"""LLM model + system prompt + OpenAI tool schemas for the Boreas Operator Agent.

These are all data — the agent loop in ``agent.py`` consumes them. Kept
separate so the prompt copy and tool schema can be reviewed / iterated
without touching agent control flow.

The prompt grounds GPT-4o as a thermal-engineer-voice operator
assistant: it reasons about the datacenter, calls tools for every
numerical claim, drives the 3D viewport, and references ASHRAE A1
thresholds when recommending operator actions.
"""

# OpenAI model used by the Agent. Keep at gpt-4o for the demo voice; the
# benchmark variant in 298AB-dt-viewer/tools/agent_eval.py uses gpt-4o-mini
# to keep golden-set runtime under 90 s.
LLM_MODEL = "gpt-4o"

# Max number of tool-call rounds per user query. 10 leaves headroom for
# multi-room comparison questions (3x set_room + 3x find_extremum + final answer).
AGENT_MAX_STEPS = 10


SYSTEM_PROMPT = (
    "You are the Boreas Operator Agent — an AI thermal engineer embedded in a 3D Omniverse Kit "
    "viewer of a datacenter Digital Twin. You have direct control over the viewport (room, field, "
    "surrogate, camera) and access to full-resolution CFD predictions for ten datacenter rooms "
    "(0-9).\n\n"
    "Available data: ten rooms each with full-resolution CFD predictions for T (°C), U_magnitude "
    "(m/s), and p (Pa). Five neural-operator surrogates are available: U-Net (22.6M params, "
    "production-recommended), FNO (28.3M), PI-FNO (28.3M), PI-U-Net (344K, fastest deep model), "
    "Transolver (545K). World axes: X = length (0-38.4 m), Y = width "
    "(0-3.84 m), Z = height (0-3.2 m), grid spacing 0.04 m. Aggregate metrics across 192 held-out "
    "test rooms are available for FNO vs U-Net comparison.\n\n"
    "For every operator question, behave as a thermal engineer briefing the facility operator:\n\n"
    "1. Investigate first. Use tools to check the current view, navigate to the relevant room or "
    "field, find extrema, and pull statistics before answering. Never invent numbers — every "
    "numerical claim must come from a tool call.\n\n"
    "2. Show, don't just tell. When you identify a hotspot or anomaly, use frame_camera to drop a "
    "marker and frame the viewport on the location so the operator sees what you are talking about. "
    "After set_room / set_field / set_surrogate, call load_scene so the change is visible.\n\n"
    "3. Answer in operator-engineer voice: cite the quantitative answer with units and world "
    "coordinates; compare against datacenter standards (ASHRAE A1 hot-aisle envelope 18-27 °C, "
    "rack-inlet control tolerance ±1 °C, CRAC delta-T 10-15 °C); explain operational "
    "implications (cooling adequacy, hotspot risk, airflow patterns, pressure imbalance); recommend "
    "immediate / long-term / monitoring actions when warranted; comment on which surrogate to trust "
    "for the field at hand on model-comparison questions.\n\n"
    "4. Multi-step reasoning is encouraged. For comparative questions across rooms, call "
    "find_extremum / get_room_stats with an explicit 'room' parameter (0 through 9) for each "
    "room — do NOT call set_room repeatedly before queries (set_room only changes the visible "
    "viewport scene; it is not required for query tools and batching set_rooms before queries "
    "leads to all queries hitting the last set room).\n\n"
    "Voice: precise, calm, actionable — a senior thermal engineer briefing a facility operator "
    "who needs to act on what you say."
)


# OpenAI function-calling tool schemas. Each entry follows the shape OpenAI's
# Chat Completions API expects under tools=[...].
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "describe_current_view",
        "description": "Report the room, field, surrogate, and mode currently rendered in the viewer.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "set_room",
        "description": "Switch the active datacenter room (0 through 9). Reloads the scene.",
        "parameters": {"type": "object",
                       "properties": {"room": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}},
                       "required": ["room"]},
    }},
    {"type": "function", "function": {
        "name": "set_field",
        "description": "Switch which CFD field is visualized.",
        "parameters": {"type": "object",
                       "properties": {"field": {"type": "string",
                                                "enum": ["T", "U_magnitude", "p"]}},
                       "required": ["field"]},
    }},
    {"type": "function", "function": {
        "name": "set_surrogate",
        "description": "Pick the surrogate model for comparison ('unet', 'fno', 'pifno', 'pi_unet', or 'transolver').",
        "parameters": {"type": "object",
                       "properties": {"model": {"type": "string", "enum": ["unet", "fno", "pifno", "pi_unet", "transolver"]}},
                       "required": ["model"]},
    }},
    {"type": "function", "function": {
        "name": "find_extremum",
        "description": "Find the highest ('max') or lowest ('min') value of a field at full resolution, "
                       "returning value + world coordinates. By default queries the currently active "
                       "room; pass 'room' (0 through 9) to query a specific room WITHOUT changing the "
                       "viewport. Use this for cross-room comparisons — pass 'room' explicitly each "
                       "call instead of calling set_room first.",
        "parameters": {"type": "object",
                       "properties": {"op": {"type": "string", "enum": ["max", "min"]},
                                      "field": {"type": "string",
                                                "enum": ["T", "U_magnitude", "p"]},
                                      "room": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                                               "description": "Optional. If omitted, uses the currently active room."}},
                       "required": ["op", "field"]},
    }},
    {"type": "function", "function": {
        "name": "get_room_stats",
        "description": "Return min, max, mean, std of a field in physical units. By default queries "
                       "the currently active room; pass 'room' (0 through 9) to query a specific room "
                       "WITHOUT changing the viewport. Use this for cross-room comparisons.",
        "parameters": {"type": "object",
                       "properties": {"field": {"type": "string",
                                                "enum": ["T", "U_magnitude", "p"]},
                                      "room": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                                               "description": "Optional. If omitted, uses the currently active room."}},
                       "required": ["field"]},
    }},
    {"type": "function", "function": {
        "name": "get_model_comparison",
        "description": "Get aggregate MAE / R² / latency for FNO vs U-Net across 192 test rooms, "
                       "optionally filtered to a specific field.",
        "parameters": {"type": "object",
                       "properties": {"field": {"type": "string",
                                                "enum": ["T", "Ux", "Uy", "Uz", "p"]}}},
    }},
    {"type": "function", "function": {
        "name": "frame_camera",
        "description": "Place a red marker at a world point (meters) and frame the viewport camera on it.",
        "parameters": {"type": "object",
                       "properties": {"x": {"type": "number"},
                                      "y": {"type": "number"},
                                      "z": {"type": "number"},
                                      "label": {"type": "string"}},
                       "required": ["x", "y", "z"]},
    }},
    {"type": "function", "function": {
        "name": "load_scene",
        "description": "Re-load the viewer with the current Room/Surrogate/Field/Mode selections. "
                       "Use after set_room / set_field / set_surrogate so the user sees the change.",
        "parameters": {"type": "object", "properties": {}},
    }},
]
