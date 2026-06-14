"""
LangGraph integration for Svitch.

Wraps a compiled LangGraph graph so every node execution, LLM call,
and tool call is automatically recorded to the Svitch audit log.

Usage:
    from langgraph.graph import StateGraph
    from svitch_tracer import SvitchTracer
    from svitch_tracer.integrations.langgraph import traced

    tracer = SvitchTracer(agent_id="loan-processor-v1")
    graph = StateGraph(...).compile()
    traced_graph = traced(graph, tracer)

    # Use exactly like graph.invoke() — audit trail happens automatically
    result = traced_graph.invoke({"messages": [...]})
"""

import uuid
from typing import Any, Optional


def traced(graph: Any, tracer: "SvitchTracer", run_id: Optional[str] = None) -> "TracedGraph":
    return TracedGraph(graph=graph, tracer=tracer, run_id=run_id)


class TracedGraph:
    def __init__(self, graph, tracer, run_id=None):
        self._graph = graph
        self._tracer = tracer
        self._run_id = run_id

    def invoke(self, input: dict, config: dict = None, **kwargs) -> dict:
        run_id = self._run_id or str(uuid.uuid4())

        with self._tracer.run(run_id=run_id) as run:
            # Record the entry point
            run.data_access(
                source="graph_input",
                fields_accessed=list(input.keys()),
                purpose="agent_execution",
            )

            # Patch callbacks to intercept LLM and tool calls
            config = config or {}
            callbacks = config.get("callbacks", [])
            svitch_cb = _SvitchCallback(run)
            config = {**config, "callbacks": callbacks + [svitch_cb]}

            try:
                result = self._graph.invoke(input, config=config, **kwargs)
                run.decision(
                    reason="graph_completed",
                    outcome="success",
                    metadata={"output_keys": list(result.keys()) if isinstance(result, dict) else []},
                )
                return result
            except Exception as e:
                run.decision(
                    reason="graph_failed",
                    outcome="error",
                    metadata={"error": str(e), "error_type": type(e).__name__},
                )
                raise

    async def ainvoke(self, input: dict, config: dict = None, **kwargs) -> dict:
        run_id = self._run_id or str(uuid.uuid4())

        with self._tracer.run(run_id=run_id) as run:
            run.data_access(
                source="graph_input",
                fields_accessed=list(input.keys()),
                purpose="agent_execution",
            )

            config = config or {}
            callbacks = config.get("callbacks", [])
            svitch_cb = _SvitchCallback(run)
            config = {**config, "callbacks": callbacks + [svitch_cb]}

            try:
                result = await self._graph.ainvoke(input, config=config, **kwargs)
                run.decision(reason="graph_completed", outcome="success")
                return result
            except Exception as e:
                run.decision(reason="graph_failed", outcome="error", metadata={"error": str(e)})
                raise

    def __getattr__(self, name):
        return getattr(self._graph, name)


class _SvitchCallback:
    """
    LangChain/LangGraph callback handler that records LLM and tool events
    to the Svitch audit log.
    """

    def __init__(self, run_context):
        self._run = run_context

    # --- LLM events ---

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs):
        self._pending_prompt = prompts[0] if prompts else ""
        self._pending_provider = serialized.get("id", ["unknown"])[-1]
        self._pending_model = kwargs.get("invocation_params", {}).get("model", "unknown")

    def on_llm_end(self, response, **kwargs):
        try:
            text = response.generations[0][0].text
        except (AttributeError, IndexError):
            text = str(response)

        self._run.llm_call(
            provider=getattr(self, "_pending_provider", "unknown"),
            model=getattr(self, "_pending_model", "unknown"),
            prompt=getattr(self, "_pending_prompt", ""),
            response=text,
        )

    def on_llm_error(self, error, **kwargs):
        self._run.decision(
            reason="llm_error",
            outcome="error",
            metadata={"error": str(error)},
        )

    # --- Tool events ---

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        self._pending_tool = serialized.get("name", "unknown")
        self._pending_tool_input = input_str

    def on_tool_end(self, output: str, **kwargs):
        self._run.tool_call(
            tool=getattr(self, "_pending_tool", "unknown"),
            input={"input": getattr(self, "_pending_tool_input", "")},
            output={"output": output},
        )

    def on_tool_error(self, error, **kwargs):
        self._run.decision(
            reason="tool_error",
            outcome="error",
            metadata={"tool": getattr(self, "_pending_tool", "unknown"), "error": str(error)},
        )

    # Satisfy LangChain callback interface
    def on_chain_start(self, *args, **kwargs): pass
    def on_chain_end(self, *args, **kwargs): pass
    def on_chain_error(self, *args, **kwargs): pass
    def on_agent_action(self, *args, **kwargs): pass
    def on_agent_finish(self, *args, **kwargs): pass
    def on_text(self, *args, **kwargs): pass
    def on_retriever_start(self, *args, **kwargs): pass
    def on_retriever_end(self, *args, **kwargs): pass
    def on_retriever_error(self, *args, **kwargs): pass
