# nodes/extractor.py
from ..state import MainState

def extract_node(state: MainState) -> dict:
    """정보추출 + 병합 - TODO: BRAIN4-XX에서 구현"""
    return {
        "extracted_info": {},
        "final_conditions": {"has_profile": False, "missing_fields": []},
    }