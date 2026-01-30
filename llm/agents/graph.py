"""LangGraph 그래프 정의"""
from langgraph.graph import StateGraph, END

from .state import MainState
from .nodes.orchestrator import orchestrate_node
from .nodes.extractor import extract_node
from .nodes.rewriter import rewrite_node
from .nodes.searcher import search_node
from .nodes.matcher import match_node
from .nodes.generator import generate_node


def route_after_orchestrator(state: MainState) -> str:
    """의도에 따라 다음 노드 결정"""
    intent = state.get("intent")
    
    if intent == "chitchat":
        return "generator"
    else:
        return "extractor"


def route_after_extractor(state: MainState) -> str:
    """정보추출 후 라우팅"""
    intent = state.get("intent")
    
    if intent == "matching":
        return "matcher"
    else:  # compare, faq, explore
        return "rewriter"


def create_graph() -> StateGraph:
    """그래프 생성"""
    graph = StateGraph(MainState)
    
    # 노드 추가
    graph.add_node("orchestrator", orchestrate_node)
    graph.add_node("extractor", extract_node)
    graph.add_node("rewriter", rewrite_node)
    graph.add_node("searcher", search_node)
    graph.add_node("matcher", match_node)
    graph.add_node("generator", generate_node)
    
    # 엣지 연결
    graph.set_entry_point("orchestrator")
    
    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "generator": "generator",
            "extractor": "extractor",
        }
    )
    
    graph.add_conditional_edges(
        "extractor",
        route_after_extractor,
        {
            "matcher": "matcher",
            "rewriter": "rewriter",
        }
    )
    
    graph.add_edge("matcher", "generator")
    graph.add_edge("rewriter", "searcher")
    graph.add_edge("searcher", "generator")
    graph.add_edge("generator", END)
    
    return graph.compile()


# 싱글톤
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph