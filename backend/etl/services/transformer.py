"""
데이터 정제 서비스 - 회의 결정사항 반영

정제 규칙:
1. 나이: 빈 값 → 키워드 기반 추론 → 기본값 19-39, 0은 유지
2. 신청기간: 전체 +2년 변환
3. 카테고리: 대분류 5개 + 중분류 보존
"""

import logging
import re
from datetime import datetime, date
from typing import Optional, Any, Tuple
from dataclasses import dataclass
from django.utils import timezone

logger = logging.getLogger(__name__)


# 나이 추론 규칙 (키워드 기반)
AGE_RULES = [
    # (키워드 리스트, min, max, 라벨)
    (['청년', '청년센터'], 19, 39, '청년'),
    (['대학생', '대학교', '대학원', '실습생'], 18, 99, '대학생'),
    (['학부모', '부모교실', '청소년기부모'], 25, 55, '학부모'),
    (['양육', '영유아', '성장지원금'], 20, 55, '양육'),
    (['장애인', '장애'], 0, 99, '장애인'),
    (['다문화', '이민자'], 0, 99, '다문화'),
    (['1인가구'], 19, 39, '1인가구'),
    (['예술인', '예술가'], 19, 65, '예술인'),
    (['어르신', '노인', '65세'], 0, 99, '전연령'),
    (['코로나', '예방접종', '백신'], 0, 99, '전연령'),
    (['상품권', '축제', '탐방'], 0, 99, '전연령'),
    (['취업', '일자리', '면접', '취업사관'], 19, 39, '청년취업'),
]
DEFAULT_MIN_AGE = 0
DEFAULT_MAX_AGE = 99


@dataclass
class TransformedPolicy:
    """변환된 정책 데이터"""
    policy_id: str  # [RENAME] plcy_no → policy_id
    title: str  # [RENAME] plcy_nm → title
    description: str  # [RENAME] plcy_expln_cn → description
    support_content: str  # [RENAME] plcy_sprt_cn → support_content

    # 나이 (정제 규칙 적용)
    age_min: Optional[int]  # [RENAME] sprt_trgt_min_age → age_min
    age_max: Optional[int]  # [RENAME] sprt_trgt_max_age → age_max

    # 소득/자격 조건
    income_level: str  # [RENAME] earn_cnd_se_cd → income_level
    income_min: Optional[int]  # [RENAME] earn_min_amt → income_min
    income_max: Optional[int]  # [RENAME] earn_max_amt → income_max
    marriage_status: str  # [RENAME] mrg_stts_cd → marriage_status
    employment_status: str  # [RENAME] job_cd → employment_status
    education_status: str  # [RENAME] school_cd → education_status

    # 신청기간 (2024→2026 변환 적용)
    apply_start_date: Optional[date]  # [RENAME] aply_start_dt → apply_start_date
    apply_end_date: Optional[date]  # [RENAME] aply_end_dt → apply_end_date
    business_start_date: Optional[date]  # [RENAME] biz_prd_bgng_ymd → business_start_date
    business_end_date: Optional[date]  # [RENAME] biz_prd_end_ymd → business_end_date

    # 신청 방법
    apply_method: str  # [RENAME] plcy_aply_mthd_cn → apply_method
    apply_url: str  # [RENAME] aply_url_addr → apply_url

    # 지역 (변경 없음)
    district: Optional[str]

    # 카테고리 (대분류 + 중분류)
    category: str  # [RENAME] lclsf_nm → category (대분류: UI 표시용)
    subcategory: str  # [RENAME] mclsf_nm → subcategory (중분류: 매칭 로직용)

    # 메타데이터
    created_at: Optional[datetime]  # [RENAME] frst_reg_dt → created_at
    updated_at: Optional[datetime]  # [RENAME] last_mdfcn_dt → updated_at


class PolicyTransformer:
    """정책 데이터 정제"""

    def transform(self, raw: dict) -> TransformedPolicy:
        # 나이 정제: 빈 값 → 키워드 추론 → 기본값, 0은 유지
        policy_name = raw.get('plcyNm', '')
        min_age, max_age = self._infer_age(
            raw.get('sprtTrgtMinAge'),
            raw.get('sprtTrgtMaxAge'),
            policy_name
        )

        # 신청기간 정제: 2024 → 2026 변환
        aply_start, aply_end = self._parse_date_range_with_year_fix(raw.get('aplyYmd', ''))

        return TransformedPolicy(
            policy_id=raw['plcyNo'],  # [RENAME] plcy_no → policy_id
            title=raw.get('plcyNm', ''),  # [RENAME] plcy_nm → title
            description=raw.get('plcyExplnCn', ''),  # [RENAME] plcy_expln_cn → description
            support_content=raw.get('plcySprtCn', ''),  # [RENAME] plcy_sprt_cn → support_content

            age_min=min_age,  # [RENAME] sprt_trgt_min_age → age_min
            age_max=max_age,  # [RENAME] sprt_trgt_max_age → age_max

            income_level=raw.get('earnCndSeCd', ''),  # [RENAME] earn_cnd_se_cd → income_level
            income_min=self._parse_int(raw.get('earnMinAmt')),  # [RENAME] earn_min_amt → income_min
            income_max=self._parse_int(raw.get('earnMaxAmt')),  # [RENAME] earn_max_amt → income_max
            marriage_status=raw.get('mrgSttsCd', ''),  # [RENAME] mrg_stts_cd → marriage_status
            employment_status=raw.get('jobCd', ''),  # [RENAME] job_cd → employment_status
            education_status=raw.get('schoolCd', ''),  # [RENAME] school_cd → education_status

            apply_start_date=aply_start,  # [RENAME] aply_start_dt → apply_start_date
            apply_end_date=aply_end,  # [RENAME] aply_end_dt → apply_end_date
            business_start_date=self._parse_date_with_year_fix(raw.get('bizPrdBgngYmd')),  # [RENAME] biz_prd_bgng_ymd → business_start_date
            business_end_date=self._parse_date_with_year_fix(raw.get('bizPrdEndYmd')),  # [RENAME] biz_prd_end_ymd → business_end_date

            apply_method=raw.get('plcyAplyMthdCn', ''),  # [RENAME] plcy_aply_mthd_cn → apply_method
            apply_url=raw.get('aplyUrlAddr', ''),  # [RENAME] aply_url_addr → apply_url

            district=self._parse_district(raw.get('rgtrInstCdNm', '')),

            category=raw.get('lclsfNm', '').strip(),  # [RENAME] lclsf_nm → category (대분류)
            subcategory=raw.get('mclsfNm', '').strip(),  # [RENAME] mclsf_nm → subcategory (중분류)

            created_at=self._parse_datetime(raw.get('frstRegDt')),  # [RENAME] frst_reg_dt → created_at
            updated_at=self._parse_datetime(raw.get('lastMdfcnDt')),  # [RENAME] last_mdfcn_dt → updated_at
        )

    def transform_many(self, raw_list: list[dict]) -> list[TransformedPolicy]:
        results = []
        errors = []

        for raw in raw_list:
            try:
                results.append(self.transform(raw))
            except Exception as e:
                policy_id = raw.get('plcyNo', 'UNKNOWN')  # [RENAME] plcy_no → policy_id
                logger.warning(f"변환 실패 ({policy_id}): {e}")
                errors.append(policy_id)

        if errors:
            logger.warning(f"총 {len(errors)}개 변환 실패")

        return results

    def _infer_age(self, raw_min: Any, raw_max: Any, policy_name: str) -> Tuple[Optional[int], Optional[int]]:
        """
        나이 추론 로직:
        1. 원본 값이 있고 0이 아니면 → 그대로 사용
        2. 빈 값이면 → 정책명 키워드로 추론
        3. 추론 실패 → 기본값 (loader에서 적용)
        4. 0은 그대로 유지
        """
        min_age = self._parse_age_value(raw_min)
        max_age = self._parse_age_value(raw_max)

        # 둘 다 유효한 값이면 그대로 반환 (0 포함)
        if min_age is not None and max_age is not None:
            return min_age, max_age

        # 빈 값이 있으면 키워드 기반 추론
        inferred_min, inferred_max = self._infer_age_from_keywords(policy_name)

        # 빈 값만 추론값으로 대체
        if min_age is None:
            min_age = inferred_min
        if max_age is None:
            max_age = inferred_max

        return min_age, max_age

    def _parse_age_value(self, value: Any) -> Optional[int]:
        """단순 파싱 (0 포함 그대로 반환)"""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _infer_age_from_keywords(self, policy_name: str) -> Tuple[Optional[int], Optional[int]]:
        """정책명 키워드로 나이 추론"""
        for keywords, min_age, max_age, label in AGE_RULES:
            for keyword in keywords:
                if keyword in policy_name:
                    logger.debug(f"나이 추론: '{policy_name}' → {label} ({min_age}-{max_age})")
                    return min_age, max_age

        # 매칭 안 되면 None (loader에서 기본값 적용)
        return None, None

    def _parse_date_with_year_fix(self, value: str) -> Optional[date]:
        """
        날짜 정제 + 전체 +2년 변환

        예: "20240916" → date(2026, 9, 16)
            "20250630" → date(2027, 6, 30)
        """
        if not value or len(value) != 8:
            return None

        try:
            parsed = datetime.strptime(value, '%Y%m%d').date()
            # 전체 +2년 (단, 2026년 미만인 경우만)
            if parsed.year < 2026:
                parsed = parsed.replace(year=parsed.year + 2)
            return parsed
        except ValueError:
            return None

    def _parse_date_range_with_year_fix(self, value: str) -> tuple[Optional[date], Optional[date]]:
        """
        날짜 범위 정제 + 전체 +2년 변환

        예: "20240916 ~ 20251231" → (date(2026,9,16), date(2027,12,31))
        """
        if not value or '~' not in value:
            return None, None

        try:
            parts = value.split('~')
            start_str = parts[0].strip()
            end_str = parts[1].strip() if len(parts) > 1 else ''

            start_dt = self._parse_date_with_year_fix(start_str) if start_str else None
            end_dt = self._parse_date_with_year_fix(end_str) if end_str else None

            return start_dt, end_dt
        except Exception:
            return None, None

    def _parse_int(self, value: Any) -> Optional[int]:
        if not value or value == '' or value == '0':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        if not value:
            return None
        try:
            # 1. 일단 문자를 날짜시간으로 바꿈 (아직 타임존 정보 없음)
            naive_dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

            # 2. Django 설정(Asia/Seoul)에 맞춰 타임존 도장을 찍어줌 (이게 핵심!)
            return timezone.make_aware(naive_dt)

        except ValueError:
            return None

    def _parse_district(self, value: str) -> Optional[str]:
        """서울특별시 은평구 → 은평구"""
        if not value or value == '서울특별시':
            return None
        return value.replace('서울특별시 ', '')
