from dotenv import load_dotenv
import os
import json
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

client = OpenAI()

EXTRACT_SYSTEM_PROMPT = """당신은 사용자의 메시지에서 복지 매칭에 필요한 정보를 추출하는 AI입니다.

다음 정보를 JSON 형식으로 추출하세요:
- age: 나이 (숫자, 없으면 null)
- income: 월소득 (숫자, 만원 단위, 없으면 null) - "백수/무직"이면 0
- income_code: 소득 조건 코드 (아래 참고, 없으면 null)
  * 소득 없음/백수/무직 → "0043001"
  * 중위소득 50% 이하 → "0043002"
  * 중위소득 100% 이하 → "0043003"
  * 소득 있음/직장인 → "0043001"
- residence: 거주지역 (예: "서울 강남구", 없으면 null)
- employment_status: 고용상태
  * "취준생", "취업준비", "구직중" → "구직중"
  * "백수", "무직" → "무직"  
  * "회사 다님", "직장인", "재직중" → "재직"
  * "대학생", "학교 다님" → "학생"
  * "프리랜서", "알바" → "프리랜서"
- housing_type: 주거형태 ("월세", "전세", "자가", "고시원", 없으면 null)
- needs: 필요한 지원 종류 (예: ["주거", "취업", "창업", "생활비"], 없으면 [])

반드시 유효한 JSON만 출력하세요. 다른 텍스트 없이 JSON만 출력하세요."""


def extract_user_info(user_message: str, conversation_history: list = None) -> dict:
    """사용자 메시지에서 복지 매칭에 필요한 정보 추출"""
    
    messages = [{"role": "system", "content": EXTRACT_SYSTEM_PROMPT}]
    
    # 이전 대화 컨텍스트 추가
    if conversation_history:
        for msg in conversation_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=500
        )
        
        result = response.choices[0].message.content.strip()
        
        # 마크다운 코드블록 제거
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        
        result = result.strip()
        return json.loads(result)
    
    except json.JSONDecodeError:
        return {}
    except Exception as e:
        print(f"정보 추출 오류: {e}")
        return {}


if __name__ == "__main__":
    # 테스트
    test_messages = [
        "27살이고 서울 강남에 살아요. 지금 취준생인데 월세가 너무 부담돼요",
        "저 25살 백수인데 뭐 받을 수 있어요?",
        "32살 프리랜서고 전세 살아요. 소득은 월 200만원 정도",
    ]
    
    for msg in test_messages:
        print(f"\n입력: {msg}")
        result = extract_user_info(msg)
        print(f"추출: {json.dumps(result, ensure_ascii=False, indent=2)}")