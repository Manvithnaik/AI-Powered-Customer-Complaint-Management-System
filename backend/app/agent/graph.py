"""
LangGraph Complaint Processing Graph

Wires the 5 nodes into a compiled StateGraph:

  START
    -> extraction_node        (Groq: llama-3.1-8b-instant)
    -> validation_node        (Pure Python)
    -> risk_assessment_node   (Groq: llama-3.3-70b-versatile)
    -> completeness_check_node (Pure Python)
    -> summary_node           (Groq: llama-3.1-8b-instant)
  END

Usage:
    from app.agent.graph import complaint_graph

    result = complaint_graph.invoke({
        "raw_text": "...",
        "extracted_fields": {},
        "validation_passed": True,
        "validation_warnings": [],
        "initial_severity": None,
        "priority": None,
        "ai_risk_rationale": None,
        "ai_completeness_check": None,
        "errors": [],
    })
"""

from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END

from .state import ComplaintState
from .nodes import (
    extraction_node,
    validation_node,
    risk_assessment_node,
    completeness_check_node,
    summary_node,
)


def build_complaint_graph():
    """
    Build and compile the complaint processing StateGraph.
    Returns a compiled graph ready to call with .invoke().
    """
    graph = StateGraph(ComplaintState)

    # ── Register Nodes ────────────────────────────────────
    graph.add_node("extraction", extraction_node)
    graph.add_node("validation", validation_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("completeness_check", completeness_check_node)
    graph.add_node("summary", summary_node)

    # ── Define Linear Flow ────────────────────────────────────
    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "validation")
    graph.add_edge("validation", "risk_assessment")
    graph.add_edge("risk_assessment", "completeness_check")
    graph.add_edge("completeness_check", "summary")
    graph.add_edge("summary", END)

    return graph.compile()


# Module-level singleton — import and call directly
complaint_graph = build_complaint_graph()


def run_complaint_pipeline(raw_text: str, current_state: Optional[Dict[str, Any]] = None) -> ComplaintState:
    """
    Convenience wrapper to run the full complaint pipeline.

    Args:
        raw_text: Raw unstructured complaint text.
        current_state: Current form draft fields (if any).

    Returns:
        The final ComplaintState after all nodes have run.
    """
    initial_state: ComplaintState = {
        "raw_text": raw_text,
        "current_state": current_state,
        "extracted_fields": {},
        "validation_passed": True,
        "validation_warnings": [],
        "initial_severity": None,
        "priority": None,
        "ai_risk_rationale": None,
        "ai_completeness_check": None,
        "ai_complaint_summary": None,
        "errors": [],
    }
    return complaint_graph.invoke(initial_state)
