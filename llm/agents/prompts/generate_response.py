from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

client = OpenAI()

RESPONSE_SYSTEM_PROMPT = """당신은 서울시 청년 복지 상담사 '복지나침반'입니다.

규칙:
1. 친근하고 따뜻한 말투로 답변하세요
2. 검색된 정책 정보만 사용하세요 (없으면 솔직히 모른다고)
3. 각 정책마다 핵심 정보를 포함하세요:
   - 정책명
   - 지원 내용 (금액, 혜택)
   - 신청 링크 (있으면)
4. 마지막에 추가 질문 유도하세요
5. 출처 표기: 각 정책 끝에 (출처: 청년정책 API) 표기

응답 형식:
1. 사용자 상황 공감 (1줄)
2. 추천 정책 목록 (각 정책별 핵심 정보)
3. 마무리 (추가 질문 유도)
"""


def generate_response(user_message: str, user_info: dict, search_results: list) -> str:
    """검색 결과를 자연스러운 답변으로 생성"""
    
    # 검색 결과를 컨텍스트로 변환
    if not search_results:
        context = "검색된 정책이 없습니다."
    else:
        context_parts = []
        for i, r in enumerate(search_results, 1):
            meta = r.metadata
            policy_info = f"""[정책 {i}]
정책명: {meta.get('plcyNm', '')}
지원내용: {r.page_content[:300]}
신청기간: {meta.get('aplyYmd', '상시')}
신청링크: {meta.get('aplyUrlAddr', '정보 없음')}
대상나이: {meta.get('minAge', 0)}~{meta.get('maxAge', 99)}세"""
            context_parts.append(policy_info)
        context = "\n\n".join(context_parts)
    
    # 사용자 정보 요약
    user_summary = f"""사용자 정보:
- 나이: {user_info.get('age', '미상')}세
- 고용상태: {user_info.get('employment_status', '미상')}
- 주거형태: {user_info.get('housing_type', '미상')}
- 거주지: {user_info.get('residence', '미상')}
- 필요: {', '.join(user_info.get('needs', [])) or '미상'}"""
    
    messages = [
        {"role": "system", "content": RESPONSE_SYSTEM_PROMPT},
        {"role": "user", "content": f"""사용자 질문: {user_message}

{user_summary}

검색된 정책 정보:
{context}

위 정보를 바탕으로 친근하게 답변해주세요."""}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"응답 생성 오류: {e}")
        return "죄송해요, 답변 생성 중 오류가 발생했어요. 다시 시도해주세요."


if __name__ == "__main__":
    # 테스트용 더미 데이터
    from langchain_core.documents import Document
    
    dummy_results = [
        Document(
            page_content="서울시 청년월세지원 사업 - 서울에 거주하는 청년의 주거비 부담완화를 위한 월 최대 20만원 지원",
            metadata={
                "plcyNm": "서울시 청년월세지원 사업",
                "aplyYmd": "2024.03 ~ 2024.04",
                "aplyUrlAddr": "https://housing.seoul.go.kr",
                "minAge": 19,
                "maxAge": 39
            }
        ),
        Document(
            page_content="서울시 취업날개서비스 - 면접 정장 대여, 이미지 컨설팅 지원",
            metadata={
                "plcyNm": "서울시 취업날개서비스",
                "aplyYmd": "상시",
                "aplyUrlAddr": "https://job.seoul.go.kr",
                "minAge": 15,
                "maxAge": 39
            }
        )
    ]
    
    user_info = {
        "age": 27,
        "employment_status": "구직중",
        "housing_type": "월세",
        "residence": "서울 강남",
        "needs": ["주거"]
    }
    
    user_message = "27살이고 서울 강남에 살아요. 지금 취준생인데 월세가 너무 부담돼요"
    
    print("=" * 50)
    print(f"질문: {user_message}")
    print("=" * 50)
    response = generate_response(user_message, user_info, dummy_results)
    print(response)