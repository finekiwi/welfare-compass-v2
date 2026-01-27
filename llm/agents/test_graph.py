# test_graph.py
from llm.agents.graph import get_graph

def test_graph():
    graph = get_graph()
    
    # 1. 그래프 생성 확인
    print("✅ 그래프 생성 성공")
    
    # 2. 실행 테스트
    result = graph.invoke({
        "user_query": "나 27살인데 뭐 받을 수 있어?",
        "user_profile": None,
    })
    print(f"✅ 실행 완료: {result.get('response')}")
    
    # 3. 시각화
    print("\n📊 Mermaid 다이어그램:")
    print(graph.get_graph().draw_mermaid())

if __name__ == "__main__":
    test_graph()