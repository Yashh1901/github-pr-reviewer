from langgraph.graph import StateGraph, END
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
import os

class PRReviewState(TypedDict):
    repo: str
    pr_number: int
    diff: str
    code_review: str
    security_review: str
    test_review: str
    final_report: str
    human_approved: bool

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )

def supervisor_node(state: PRReviewState) -> PRReviewState:
    # TODO: route to specialized agents in Phase 3
    return state

def build_supervisor_graph() -> StateGraph:
    graph = StateGraph(PRReviewState)
    graph.add_node("supervisor", supervisor_node)
    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", END)
    return graph.compile() 