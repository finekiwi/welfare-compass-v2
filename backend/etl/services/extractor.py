"""온통청년 API에서 정책 데이터 추출 및 JSON 저장"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
import requests
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class PolicyExtractor:
    """온통청년 API 호출 및 JSON 저장"""

    BASE_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
    
    # 원본 JSON 저장 경로 (data/raw/)
    RAW_DATA_DIR = Path(settings.BASE_DIR).parent / 'data' / 'raw'

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'YOUTH_API_KEY', None)
        if not self.api_key:
            raise ValueError("YOUTH_API_KEY 환경변수 필요")
        self.page_size = 100  # 전체 정책 수집을 위해 100으로 설정
        self.max_retries = 3
        self.retry_delay = 2

    def fetch_and_save(self, region_code: str = "11000") -> Path:
        """
        API에서 데이터 수집 후 JSON 파일로 저장
        
        Returns:
            저장된 JSON 파일 경로
        """
        all_policies = self._fetch_all_pages(region_code)
        
        # 서울시만 필터링
        seoul_policies = [
            p for p in all_policies
            if p.get('rgtrHghrkInstCdNm') == '서울특별시'
        ]
        
        logger.info(f"수집 완료: 전체 {len(all_policies)} → 서울 {len(seoul_policies)}")
        
        # JSON 파일로 저장 (원본 보존)
        json_path = self._save_to_json(seoul_policies)
        
        return json_path

    def load_from_json(self, json_path: Optional[Path] = None) -> list[dict]:
        """
        JSON 파일에서 정책 데이터 로드
        
        Args:
            json_path: JSON 파일 경로. None이면 최신 파일 사용
            
        Returns:
            정책 딕셔너리 리스트
        """
        if json_path is None:
            json_path = self._get_latest_json()
            
        if json_path is None or not json_path.exists():
            raise FileNotFoundError("정책 JSON 파일이 없습니다. fetch_and_save()를 먼저 실행하세요.")
            
        with open(json_path, 'r', encoding='utf-8') as f:
            policies = json.load(f)
            
        logger.info(f"JSON 로드 완료: {json_path} ({len(policies)}개)")
        return policies

    def _fetch_all_pages(self, region_code: str) -> list[dict]:
        """모든 페이지에서 정책 수집"""
        all_policies = []
        page = 1

        logger.info(f"정책 수집 시작 (지역: {region_code})")

        while True:
            policies, total = self._fetch_page_with_retry(page, region_code)
            all_policies.extend(policies)

            logger.info(f"페이지 {page}: {len(policies)}개 (누적: {len(all_policies)}/{total})")

            if len(all_policies) >= total:
                break
            page += 1
            time.sleep(0.5)

        return all_policies

    def _fetch_page_with_retry(self, page: int, region_code: str) -> tuple[list, int]:
        """재시도 로직이 포함된 페이지 호출"""
        for attempt in range(self.max_retries):
            try:
                return self._fetch_page(page, region_code)
            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"페이지 {page} 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"페이지 {page} 최종 실패: {e}")
                    raise

    def _fetch_page(self, page: int, region_code: str) -> tuple[list, int]:
        params = {
            "apiKeyNm": self.api_key,
            "pageNum": page,
            "pageSize": self.page_size,
            "rtnType": "json",
            "zipCd": region_code,
        }

        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        policies = data['result'].get('youthPolicyList', [])
        total = data['result'].get('pagging', {}).get('totCount', 0)

        return policies, total

    def _save_to_json(self, policies: list[dict]) -> Path:
        """JSON 파일로 저장"""
        self.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # 타임스탬프 포함 파일명
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"seoul_policies_{timestamp}.json"
        json_path = self.RAW_DATA_DIR / filename
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(policies, f, ensure_ascii=False, indent=2)
            
        logger.info(f"JSON 저장 완료: {json_path} ({len(policies)}개)")
        
        # 최신 파일 심볼릭 링크 업데이트 (선택사항)
        latest_path = self.RAW_DATA_DIR / 'seoul_policies.json'
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(filename)
        
        return json_path

    def _get_latest_json(self) -> Optional[Path]:
        """최신 JSON 파일 경로 반환"""
        latest_path = self.RAW_DATA_DIR / 'seoul_policies.json'
        if latest_path.exists():
            return latest_path.resolve()
        return None
