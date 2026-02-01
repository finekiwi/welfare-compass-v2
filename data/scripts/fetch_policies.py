import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTH_API_KEY")
BASE_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"

def fetch_seoul_policies():
    """서울 정책 전체 호출"""
    all_policies = []
    page = 1
    page_size = 100
    
    while True:
        params = {
            "apiKeyNm": API_KEY,
            "pageNum": page,
            "pageSize": page_size,
            "rtnType": "json",
            "zipCd": "11000" 
        }
        
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        policies = data['result']['youthPolicyList']
        all_policies.extend(policies)
        
        total = data['result']['pagging']['totCount']
        print(f"페이지 {page}: {len(policies)}개 (누적 {len(all_policies)}/{total})")
        
        if len(all_policies) >= total:
            break
        
        page += 1
    
    seoul_policies = [
        p for p in all_policies 
        if p.get('rgtrHghrkInstCdNm') == '서울특별시'
    ]
    
    print(f"\n필터링 전: {len(all_policies)}개")
    print(f"필터링 후: {len(seoul_policies)}개")
    
    return seoul_policies

if __name__ == "__main__":
    policies = fetch_seoul_policies()
    
    output_path = "data/raw/seoul_policies.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(policies, f, ensure_ascii=False, indent=2)
    
    print(f"\n총 {len(policies)}개 저장 완료: {output_path}")