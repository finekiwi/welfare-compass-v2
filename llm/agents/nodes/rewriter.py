# nodes/rewriter.py
from ..state import MainState

def rewrite_node(state: MainState) -> dict:
    """쿼리 리라이터 - TODO: BRAIN4-XX에서 구현"""
    return {"rewritten_query": state.get("user_query", "")}