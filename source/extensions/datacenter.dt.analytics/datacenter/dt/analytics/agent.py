"""OpenAI tool-calling agent loop for the Boreas Operator.

The ``Agent`` class encapsulates the LLM call surface (HTTP to OpenAI's
Chat Completions API + multi-step tool-calling loop). It depends on the
prompts module for the system prompt + tool schemas, and on a caller-
supplied ``dispatch_tool`` callable to actually execute tools against
the extension's state and viewport.

Keeping the agent loop in one file makes it easier to swap providers,
add streaming, or async-ify without touching extension lifecycle.
"""

import json
import os
import urllib.request

from .log import logger
from .prompts import LLM_MODEL, AGENT_MAX_STEPS, SYSTEM_PROMPT, TOOL_SCHEMAS


class Agent:
    """Run a tool-calling conversation against OpenAI.

    Parameters
    ----------
    dispatch_tool : Callable[[str, dict], dict]
        Executes a named tool with the given JSON arguments. Returns
        the tool's result dict (will be serialized as the tool message
        content). Errors should be returned as ``{"error": "..."}``.
    describe_view : Callable[[], dict]
        Returns the current viewer state (room/field/surrogate/mode)
        injected into the user message as context.
    """

    def __init__(self, dispatch_tool, describe_view):
        self._dispatch_tool = dispatch_tool
        self._describe_view = describe_view

    def run(self, user_text):
        """Returns (final_text, trace_list)."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Current view: {json.dumps(self._describe_view())}\n"
                f"User question: {user_text}"},
        ]
        trace = []
        for _ in range(AGENT_MAX_STEPS):
            resp = self._openai_chat(messages, tools=TOOL_SCHEMAS)
            if resp is None:
                return "OpenAI call failed.", trace
            msg = resp["choices"][0]["message"]
            tool_calls = msg.get("tool_calls") or []
            messages.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            })
            if not tool_calls:
                return (msg.get("content") or "(no answer)"), trace
            for tc in tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                trace.append(name + ("(" + ",".join(f"{k}={v}" for k, v in args.items()) + ")" if args else "()"))
                result = self._dispatch_tool(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result)[:1500],
                })
        return "Max reasoning steps reached.", trace

    @staticmethod
    def _openai_chat(messages, tools=None):
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            return None
        body = {"model": LLM_MODEL, "messages": messages, "temperature": 0}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            data=json.dumps(body).encode(),
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            logger.warning(f"openai_chat failed: {type(e).__name__}: {e}")
            return None
