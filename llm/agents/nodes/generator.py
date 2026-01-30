# nodes/generator.py
from ..state import MainState

def generate_node(state: MainState) -> dict:
    """응답생성 - TODO: BRAIN4-XX에서 구현"""
    return {"response": f"[{state.get('intent')}] 응답 예정"}