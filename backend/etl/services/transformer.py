"""
데이터 정제 서비스 - 회의 결정사항 반영

정제 규칙:
1. 나이: 빈 값 → 키워드 기반 추론 → 기본값 19-39, 0은 유지
2. 신청기간: 2024년은 +2년, 2025년은 +1년 보정
3. 카테고리: 대분류 5개 + 중분류 보존
"""

import logging
import re
from datetime import datetime, date
from typing import Optional, Any, Tuple
from dataclasses import dataclass
from django.utils import timezone
from .overrides import apply_overrides
from policies.services.matching_keys import (
    SBIZ_CODE_LOW_INCOME,
    SBIZ_CODE_SINGLE_PARENT,
    SBIZ_CODE_DISABLED,
)

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

# 서울 25개 구 zipCd → 한글 매핑
ZIPCD_TO_DISTRICT = {
    '11110': '종로구',
    '11140': '중구',
    '11170': '용산구',
    '11200': '성동구',
    '11215': '광진구',
    '11230': '동대문구',
    '11260': '중랑구',
    '11290': '성북구',
    '11305': '강북구',
    '11320': '도봉구',
    '11350': '노원구',
    '11380': '은평구',
    '11410': '서대문구',
    '11440': '마포구',
    '11470': '양천구',
    '11500': '강서구',
    '11530': '구로구',
    '11545': '금천구',
    '11560': '영등포구',
    '11590': '동작구',
    '11620': '관악구',
    '11650': '서초구',
    '11680': '강남구',
    '11710': '송파구',
    '11740': '강동구',
}


def _is_newlywed_exclusive(policy_text: str) -> bool:
    """
    신혼부부 '전용' 정책인지 텍스트에서 판단
    (API에 신혼부부 코드가 없으므로 텍스트 파싱 필요)

    Returns:
        True: 신혼부부 전용 (비신혼부부 제외해야 함)
        False: 신혼부부 우대/가점 또는 해당없음 (모두 포함)
    """
    if '신혼' not in policy_text:
        return False

    # 포용적 표현 (이게 있으면 전용 아님 - 일반 청년도 지원 가능)
    inclusive_patterns = [
        '신혼부부 우대', '신혼부부 우선', '신혼부부 가점', '신혼부부 가산',
        '신혼부부도 가능', '신혼부부도 신청', '신혼부부도 지원',
        '신혼부부 포함', '신혼부부 해당자',
        '신혼부부인 경우 우대', '신혼부부인 경우 가점',
    ]

    for pattern in inclusive_patterns:
        if pattern in policy_text:
            return False

    # 배타적 표현 (이게 있으면 전용 - 신혼부부만 지원 가능)
    exclusive_patterns = [
        '신혼부부 전용', '신혼부부만 가능', '신혼부부만 신청',
        '신혼부부만 지원', '신혼부부에 한해', '신혼부부에 한함',
        '신혼부부에 한하여', '신혼부부 가구만',
    ]

    for pattern in exclusive_patterns:
        if pattern in policy_text:
            return True

    # 패턴 없으면 포용적으로 판단 (전용 아님)
    return False


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

    # 신청기간 연도 보정 적용 (2024:+2, 2025:+1)
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

    # 특수조건
    sbiz_cd: str
    is_for_single_parent: bool
    is_for_disabled: bool
    is_for_low_income: bool
    is_for_newlywed: bool

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

        # 신청기간 정제: 연도 보정 (2024:+2, 2025:+1)
        aply_start, aply_end = self._parse_date_range_with_year_fix(raw.get('aplyYmd', ''))

        raw_description = raw.get('plcyExplnCn') or ''
        raw_support = raw.get('plcySprtCn') or ''

        normalized_title = self._normalize_text_years(raw.get('plcyNm', ''))
        normalized_description = self._normalize_text_years(raw_description)
        normalized_support_content = self._normalize_text_years(raw_support)
        normalized_apply_method = self._normalize_text_years(raw.get('plcyAplyMthdCn', ''))

        # [BRAIN4-45 A1-1] 특수조건 파싱
        sbiz_cd = raw.get('sbizCd') or ''
        is_for_single_parent = SBIZ_CODE_SINGLE_PARENT in sbiz_cd
        is_for_disabled = SBIZ_CODE_DISABLED in sbiz_cd
        is_for_low_income = SBIZ_CODE_LOW_INCOME in sbiz_cd
        is_for_newlywed = _is_newlywed_exclusive(
            f"{raw.get('plcyNm', '')} {raw_description} {raw_support}"
        )

        # [BRAIN4-37 C02] 정책별 override 적용
        override_fields, _logs = apply_overrides(
            raw['plcyNo'],
            {
                'education_status': raw.get('schoolCd', ''),
                'employment_status': raw.get('jobCd', ''),
            },
        )

        return TransformedPolicy(
            policy_id=raw['plcyNo'],  # [RENAME] plcy_no → policy_id
            title=normalized_title,  # [RENAME] plcy_nm → title
            description=normalized_description,  # [RENAME] plcy_expln_cn → description
            support_content=normalized_support_content,  # [RENAME] plcy_sprt_cn → support_content

            age_min=min_age,  # [RENAME] sprt_trgt_min_age → age_min
            age_max=max_age,  # [RENAME] sprt_trgt_max_age → age_max

            income_level=raw.get('earnCndSeCd', ''),  # [RENAME] earn_cnd_se_cd → income_level
            income_min=self._parse_int(raw.get('earnMinAmt')),  # [RENAME] earn_min_amt → income_min
            income_max=self._parse_int(raw.get('earnMaxAmt')),  # [RENAME] earn_max_amt → income_max
            marriage_status=raw.get('mrgSttsCd', ''),  # [RENAME] mrg_stts_cd → marriage_status
            employment_status=override_fields['employment_status'],
            education_status=override_fields['education_status'],

            apply_start_date=aply_start,  # [RENAME] aply_start_dt → apply_start_date
            apply_end_date=aply_end,  # [RENAME] aply_end_dt → apply_end_date
            business_start_date=self._parse_date_with_year_fix(raw.get('bizPrdBgngYmd')),  # [RENAME] biz_prd_bgng_ymd → business_start_date
            business_end_date=self._parse_date_with_year_fix(raw.get('bizPrdEndYmd')),  # [RENAME] biz_prd_end_ymd → business_end_date

            apply_method=normalized_apply_method,  # [RENAME] plcy_aply_mthd_cn → apply_method
            apply_url=raw.get('aplyUrlAddr', ''),  # [RENAME] aply_url_addr → apply_url

            district=self._parse_district(raw.get('zipCd', ''), raw.get('rgtrInstCdNm', '')),

            category=raw.get('lclsfNm', '').strip(),  # [RENAME] lclsf_nm → category (대분류)
            subcategory=raw.get('mclsfNm', '').strip(),  # [RENAME] mclsf_nm → subcategory (중분류)

            sbiz_cd=sbiz_cd,
            is_for_single_parent=is_for_single_parent,
            is_for_disabled=is_for_disabled,
            is_for_low_income=is_for_low_income,
            is_for_newlywed=is_for_newlywed,

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
        날짜 정제 + 연도 보정

        예: "20240916" → date(2026, 9, 16)
            "20250630" → date(2026, 6, 30)
            "20260101" → date(2026, 1, 1)
        """
        if not value or len(value) != 8:
            return None

        try:
            parsed = datetime.strptime(value, '%Y%m%d').date()
            # 회의 결정 반영: 2024는 +2년, 2025는 +1년
            if parsed.year == 2024:
                parsed = parsed.replace(year=parsed.year + 2)
            elif parsed.year == 2025:
                parsed = parsed.replace(year=parsed.year + 1)
            return parsed
        except ValueError:
            return None

    def _parse_date_range_with_year_fix(self, value: str) -> tuple[Optional[date], Optional[date]]:
        """
        날짜 범위 정제 + 연도 보정

        예: "20240916 ~ 20251231" → (date(2026,9,16), date(2026,12,31))
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
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _normalize_text_years(self, value: str) -> str:
        """
        텍스트에 포함된 연도 표기를 운영 연도 기준으로 보정.
        - 2024 -> 2026
        - 2025 -> 2026
        """
        if not value:
            return ''

        normalized = re.sub(r'(?<!\d)2024(?!\d)', '2026', value)
        normalized = re.sub(r'(?<!\d)2025(?!\d)', '2026', normalized)
        return normalized

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

    def _parse_district(self, zip_cd: str, rgtr_inst: str) -> Optional[str]:
        """
        zipCd 코드 → 한글 구 이름 변환.

        1순위: zipCd로 매핑 (11380 → 은평구)
        2순위: rgtrInstCdNm fallback (서울특별시 은평구 → 은평구)
        - 11000(서울시 전체), 쉼표 다중 코드 → None (구 제한 없음)
        """
        # 1순위: zipCd
        if zip_cd:
            # 쉼표로 여러 코드 → 광역(구 제한 없음)
            if ',' in zip_cd:
                return None
            district = ZIPCD_TO_DISTRICT.get(zip_cd.strip())
            if district:
                return district
            # 11000(서울시 전체) 또는 매핑 없는 코드 → None
            return None

        # 2순위: rgtrInstCdNm fallback
        if not rgtr_inst or rgtr_inst == '서울특별시':
            return None
        if rgtr_inst.startswith('서울특별시 '):
            candidate = rgtr_inst.replace('서울특별시 ', '')
            if candidate.endswith('구'):
                return candidate
        return None
