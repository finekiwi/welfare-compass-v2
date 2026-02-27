"""
정책 매칭 서비스 - Django 모델 기반

[BRAIN4-14] 버그 수정 내역:
1. 특수조건 필터링: 텍스트 파싱 → API 코드 기반 Boolean 필드
2. 점수 계산: 신혼부부 청년 감점 로직 제거

[BRAIN4-31] 회원용/챗봇용 분리:
- match_policies_for_web(profile): 회원 웹용 - 전체 정책 반환
- match_policies_for_chatbot(user_info, top_k): 챗봇용 - 상위 N개 반환
- match_policies(): deprecated 래퍼 (하위 호환용)
"""
import logging
import re
from django.db.models import Q
from policies.models import Policy
from policies.services.matching_keys import (
    SBIZ_CODE_SME,
    SBIZ_CODE_MILITARY,
    RESTRICTION_CODE_JOB,
    RESTRICTION_CODE_EDUCATION,
    RESTRICTION_CODE_MARRIAGE,
    EDUCATION_ALSO_MATCH,
    CHATBOT_TOP_K,
    KNOWN_EDUCATION_CODES,
    KNOWN_JOB_CODES,
    INCOME_CODE_ANY,
    INCOME_CODE_ANNUAL,
    INCOME_CODE_OTHER,
    parse_code_string,
    normalize_user_info,
)

logger = logging.getLogger(__name__)


# =============================================================================
# [BRAIN4-31] Public API - 회원용/챗봇용 분리
# =============================================================================

def match_policies_for_web(profile, exclude_policy_ids=None, include_category=None):
    """
    회원 웹용 정책 매칭 - 전체 정책 반환

    [BRAIN4-31] 신규 함수
    - 회원 "내게 맞는 정책" 페이지에서 사용
    - 조건에 맞는 모든 정책을 우선순위 순으로 반환
    - 프론트에서 페이지네이션/무한스크롤 처리

    Args:
        profile: accounts.Profile 인스턴스
        exclude_policy_ids: 제외할 정책 ID 리스트
        include_category: 특정 카테고리만 포함

    Returns:
        list of (Policy, score) tuples - 전체 반환
    """
    user_info = profile.to_matching_dict()
    return _match_policies_core(
        user_info,
        exclude_policy_ids=exclude_policy_ids,
        include_category=include_category,
        limit=None,
        max_per_category=None,
    )


def match_policies_for_chatbot(user_info: dict, top_k: int = CHATBOT_TOP_K):
    """
    챗봇용 정책 매칭 - 상위 N개만 반환

    [BRAIN4-34] top_k 기본값 CHATBOT_TOP_K(5)로 변경

    Args:
        user_info: 사용자 정보 dict (Profile.to_matching_dict() 형식)
            필수: age, residence 중 하나 이상 권장
            선택: employment_status, job_code, education_code, marriage_code,
                  housing_type, income, household_size, has_children,
                  children_ages, special_conditions, needs
        top_k: 반환할 최대 정책 수 (기본값 5)

    Returns:
        list of (Policy, score) tuples - 상위 top_k개
    """
    return _match_policies_core(
        user_info,
        exclude_policy_ids=None,
        include_category=None,
        limit=top_k,
        max_per_category=2,
    )


def match_policies(profile, exclude_policy_ids=None, include_category=None, limit=10):
    """
    [DEPRECATED] 기존 호환용 래퍼

    [BRAIN4-31] 변경사항:
    - 새 코드는 match_policies_for_web() 또는 match_policies_for_chatbot() 사용 권장
    - 기존 views.py 등 호출처와의 하위 호환성 유지

    Args:
        profile: accounts.Profile 인스턴스
        exclude_policy_ids: 제외할 정책 ID 리스트
        include_category: 특정 카테고리만 포함
        limit: 최대 반환 개수 (기본값 10)

    Returns:
        list of (Policy, score) tuples
    """
    user_info = profile.to_matching_dict()
    return _match_policies_core(
        user_info,
        exclude_policy_ids=exclude_policy_ids,
        include_category=include_category,
        limit=limit,
        max_per_category=2,
    )


# =============================================================================
# [BRAIN4-31] 내부 핵심 함수
# =============================================================================

def _match_policies_core(
    user_info: dict,
    exclude_policy_ids=None,
    include_category=None,
    limit=None,
    max_per_category=2,
):
    """
    정책 매칭 핵심 로직 (내부 함수)

    [BRAIN4-31] 기존 match_policies() 로직을 내부 함수로 이동
    - user_info dict를 직접 받아 처리
    - limit=None이면 전체 반환

    Args:
        user_info: 사용자 정보 dict
        exclude_policy_ids: 제외할 정책 ID 리스트
        include_category: 특정 카테고리만 포함
        limit: 최대 반환 개수 (None이면 전체 반환)
        max_per_category: 카테고리별 최대 개수 (None이면 제한 없음)

    Returns:
        list of (Policy, score) tuples
    """
    # [BRAIN4-34] 특수조건 alias 정규화
    user_info = normalize_user_info(user_info)

    # Step 1: Django ORM으로 기본 필터링
    queryset = _apply_base_filters(user_info, exclude_policy_ids, include_category)

    # Step 2: 정책 리스트 가져오기
    policies = list(queryset.prefetch_related('categories'))

    # Step 3: 코드 필터(job/education/marriage) + 특수조건 필터
    policies = [p for p in policies if _passes_profile_code_filters(p, user_info)]
    policies = [p for p in policies if _check_special_conditions(p, user_info)]

    # Step 4: 우선순위 점수 계산
    relevant_categories = _get_relevant_categories(user_info)
    scored_policies = []
    for policy in policies:
        score = _calc_priority(policy, user_info, relevant_categories)
        scored_policies.append((policy, score))

    # Step 5: 정렬
    scored_policies.sort(key=lambda x: -x[1])

    # Step 6: 카테고리별 분산 선택
    if limit is None:
        # [BRAIN4-35] 전체보기: 다양성 선택 스킵, 점수순 전체 반환 (페이지네이션은 뷰에서 처리)
        final_results = scored_policies
    else:
        # 챗봇/홈 추천: 카테고리별 분산 선택 적용
        final_results = _select_diverse_categories(
            scored_policies, max_per_category=max_per_category, limit=limit
        )

    return final_results


def _apply_base_filters(user_info, exclude_policy_ids, include_category):
    """
    Django ORM으로 기본 필터 적용

    [BRAIN4-31] 변경사항:
    - 취업 요건(jobCd), 학력 요건(schoolCd), 결혼 상태(mrgSttsCd) 필터링 추가
    - 기존: 나이/거주지만 필터링 → 28% 정책(114개)의 취업 요건이 무시됨
    - 개선: API 코드 기반 정확한 필터링

    [BRAIN4-37 C06] 변경사항:
    - unknown 코드(예: 0049009, 0013009 등)로 인한 부당 탈락 방지를 위해
      job/education의 최종 판정은 Python 단계(_passes_profile_code_filters)에서 수행
    - 여기서는 age/residence/marriage 중심의 coarse filter만 적용
    """
    queryset = Policy.objects.all()

    # 제외할 정책
    if exclude_policy_ids:
        queryset = queryset.exclude(policy_id__in=exclude_policy_ids)  # [RENAME] plcy_no__in → policy_id__in

    # 특정 카테고리만
    if include_category:
        queryset = queryset.filter(categories__name__icontains=include_category)

    # 나이 필터
    age = user_info.get('age')
    if age:
        queryset = queryset.filter(
            Q(age_min__isnull=True) | Q(age_min__lte=age),  # [RENAME] sprt_trgt_min_age → age_min
            Q(age_max__isnull=True) | Q(age_max__gte=age)  # [RENAME] sprt_trgt_max_age → age_max
        )

    # 거주지 필터 (서울 내 구)
    residence = user_info.get('residence', '')
    if residence:
        # 해당 구 정책 + 서울시 전체 정책(district=NULL)
        queryset = queryset.filter(
            Q(district__isnull=True) |
            Q(district='') |
            Q(district=residence)
        )

    # =========================================================================
    # [BRAIN4-31] 결혼 상태 필터링 (mrgSttsCd)
    # =========================================================================
    marriage_code = user_info.get('marriage_code', '')
    if marriage_code:
        queryset = queryset.filter(
            Q(marriage_status='') |
            Q(marriage_status__isnull=True) |
            Q(marriage_status__contains=RESTRICTION_CODE_MARRIAGE) |  # 제한없음
            Q(marriage_status__contains=marriage_code)
        )

    return queryset.distinct()


def _log_unknown_codes(policy, field_name: str, unknown_codes: set[str]) -> None:
    """unknown 코드 감지 로그"""
    if not unknown_codes:
        return
    policy_id = getattr(policy, 'policy_id', 'UNKNOWN')
    logger.warning(
        "Unknown policy code detected: policy_id=%s field=%s unknown_codes=%s",
        policy_id,
        field_name,
        ",".join(sorted(unknown_codes)),
    )


def _matches_job_requirement(policy, user_info: dict) -> bool:
    """취업 요건 매칭 (unknown-only fail-open, mixed는 known 우선)"""
    job_code = user_info.get('job_code', '')
    policy_job = policy.employment_status or ''
    if not job_code or not policy_job:
        return True

    policy_codes = parse_code_string(policy_job)
    if not policy_codes:
        return True

    if RESTRICTION_CODE_JOB in policy_codes:
        return True

    known_codes = (policy_codes & KNOWN_JOB_CODES) - {RESTRICTION_CODE_JOB}
    unknown_codes = policy_codes - KNOWN_JOB_CODES
    _log_unknown_codes(policy, 'employment_status', unknown_codes)

    # unknown-only면 탈락시키지 않음
    if not known_codes and unknown_codes:
        return True

    # known+unknown 혼재면 known만 기준으로 평가
    if known_codes:
        return job_code in known_codes

    return True


def _matches_education_requirement(policy, user_info: dict) -> bool:
    """학력 요건 매칭 (unknown-only fail-open, mixed는 known 우선)"""
    education_code = user_info.get('education_code', '')
    policy_edu = policy.education_status or ''
    if not education_code or not policy_edu:
        return True

    policy_codes = parse_code_string(policy_edu)
    if not policy_codes:
        return True

    if RESTRICTION_CODE_EDUCATION in policy_codes:
        return True

    known_codes = (policy_codes & KNOWN_EDUCATION_CODES) - {RESTRICTION_CODE_EDUCATION}
    unknown_codes = policy_codes - KNOWN_EDUCATION_CODES
    _log_unknown_codes(policy, 'education_status', unknown_codes)

    # unknown-only면 탈락시키지 않음
    if not known_codes and unknown_codes:
        return True

    # known+unknown 혼재면 known만 기준으로 평가
    if known_codes:
        allowed_codes = {education_code, *EDUCATION_ALSO_MATCH.get(education_code, [])}
        return bool(allowed_codes & known_codes)

    return True


def _matches_marriage_requirement(policy, user_info: dict) -> bool:
    """결혼 상태 요건 매칭"""
    marriage_code = user_info.get('marriage_code', '')
    policy_mrg = policy.marriage_status or ''
    if not marriage_code or not policy_mrg:
        return True

    policy_codes = parse_code_string(policy_mrg)
    if not policy_codes:
        return True

    if RESTRICTION_CODE_MARRIAGE in policy_codes:
        return True

    return marriage_code in policy_codes


# =============================================================================
# [BRAIN4-37] 2026 기준중위소득 (월, 원) — 보건복지부 고시
# =============================================================================

_MEDIAN_INCOME_2026_MONTHLY = {
    1: 2_564_238,
    2: 4_199_292,
    3: 5_367_880,
    4: 6_509_816,
    5: 7_571_462,
    6: 8_555_952,
}


def _annual_income_to_median_pct(annual_income_man_won, household_size) -> float | None:
    """
    연소득(만원) + 가구원수 → 중위소득 대비 % 반환.

    Args:
        annual_income_man_won: 연소득 (만원 단위)
        household_size: 가구원 수

    Returns:
        중위소득 대비 퍼센트 (예: 50.0), 계산 불가 시 None
    """
    if annual_income_man_won is None or household_size is None:
        return None
    if household_size <= 0:
        return None
    # 6인 초과 → 6인 cap
    capped_size = min(household_size, 6)
    monthly_median = _MEDIAN_INCOME_2026_MONTHLY.get(capped_size)
    if monthly_median is None:
        return None
    annual_median = monthly_median * 12
    annual_income_won = annual_income_man_won * 10_000
    return (annual_income_won / annual_median) * 100


def _matches_income_requirement(policy, user_info: dict) -> bool:
    """
    소득 요건 매칭.

    소득 코드는 3종(무관/연소득/기타)뿐이므로 ETL 한글 변환 대신
    코드 직접 비교 (오타 방지, API 원본 대조 용이).

    - 0043001(무관) / 0043003(기타) / 빈값 / 알수없는코드 → True (pass)
    - 0043002(연소득) → user income <= policy.income_max
    - 0043002인데 income_max is None or <=0 → True (fail-open, 직접확인 필요)
    - user income 미입력 → True (fail-open)
    """
    income_code = policy.income_level or ''

    # 빈값 → pass
    if not income_code:
        return True

    # 무관 / 기타 → pass
    if income_code in (INCOME_CODE_ANY, INCOME_CODE_OTHER):
        return True

    # 알수없는 코드 → fail-open
    if income_code != INCOME_CODE_ANNUAL:
        policy_id = getattr(policy, 'policy_id', 'UNKNOWN')
        logger.warning(
            "Unknown income code '%s' for policy %s – fail-open",
            income_code,
            policy_id,
        )
        return True

    # income_code == INCOME_CODE_ANNUAL ('0043002')
    policy_max = policy.income_max
    if policy_max is None or policy_max <= 0:
        return True  # fail-open: earnMaxAmt 미설정

    user_income = user_info.get('income')
    if user_income is None:
        return True  # fail-open: 사용자 소득 미입력

    return user_income <= policy_max


def _passes_profile_code_filters(policy, user_info: dict) -> bool:
    """job/education/marriage/income 코드 필터 종합 판정"""
    return (
        _matches_job_requirement(policy, user_info) and
        _matches_education_requirement(policy, user_info) and
        _matches_marriage_requirement(policy, user_info) and
        _matches_income_requirement(policy, user_info)
    )


# =============================================================================
# [BRAIN4-14] 특수조건 필터링 - 텍스트 파싱 → Boolean 필드 기반
# [BRAIN4-31] 중소기업/군인 특수조건 추가
# =============================================================================

def _check_special_conditions(policy, user_info):
    """
    특수조건 체크 - Policy 모델의 Boolean 필드 + sbiz_cd 기반

    [BRAIN4-14 개선]
    - 기존: 텍스트에 "신혼" 있으면 무조건 제외 → "우대" 정책도 제외되는 버그
    - 개선: ETL에서 "전용" 여부를 Boolean 필드로 저장 → 정확한 필터링

    [BRAIN4-31] 추가:
    - 중소기업(0014001), 군인(0014007) 특수조건 필터링
    - sbiz_cd 필드에서 직접 코드 체크 (Boolean 필드 없음)
    """
    # [BRAIN4-34] 정규화 후이므로 canonical 값만 비교
    user_special = user_info.get('special_conditions', [])

    # 한부모 전용 정책 (sbizCd: 0014004)
    if policy.is_for_single_parent:
        if '한부모' not in user_special:
            return False

    # 장애인 전용 정책 (sbizCd: 0014005)
    if policy.is_for_disabled:
        if '장애' not in user_special:
            return False

    # 기초수급자 전용 정책 (sbizCd: 0014003)
    if policy.is_for_low_income:
        if '기초수급' not in user_special:
            return False

    # 신혼부부 전용 정책 (텍스트 파싱 - API 코드 없음)
    if policy.is_for_newlywed:
        if '신혼' not in user_special:
            return False

    # 중소기업/군인 전용 정책 (sbiz_cd 코드)
    policy_sbiz = policy.sbiz_cd or ''

    if SBIZ_CODE_SME in policy_sbiz:
        if '중소기업' not in user_special:
            return False

    if SBIZ_CODE_MILITARY in policy_sbiz:
        if '군인' not in user_special:
            return False

    # 1인가구 체크 (별도 Boolean 필드 없음 - 텍스트 기반 유지)
    policy_text = f"{policy.description or ''} {policy.support_content or ''}"  # [RENAME] plcy_expln_cn → description, plcy_sprt_cn → support_content
    if '1인가구 전용' in policy_text or '1인가구만' in policy_text:
        household_size = user_info.get('household_size')
        if household_size and household_size != 1:
            return False

    return True


def is_policy_matching_user(policy, user_info: dict) -> bool:
    """
    정책이 사용자 정보와 매칭되는지 확인 (공통 함수)

    notifications/services.py 등 다른 모듈에서 import하여 사용
    매칭 기준 변경 시 이 함수만 수정하면 됨 (DRY 원칙)

    [BRAIN4-31] 변경사항:
    - 취업 요건(jobCd), 학력 요건(schoolCd), 결혼 상태(mrgSttsCd) 체크 추가
    - _apply_base_filters()와 동일한 로직 적용

    Args:
        policy: Policy 모델 인스턴스
        user_info: Profile.to_matching_dict() 결과

    Returns:
        bool: 매칭 여부
    """
    # [BRAIN4-34] 특수조건 alias 정규화
    user_info = normalize_user_info(user_info)

    # 1. 나이 체크
    user_age = user_info.get('age')
    if user_age is not None:
        if policy.age_min and user_age < policy.age_min:
            return False
        if policy.age_max and user_age > policy.age_max:
            return False

    # 2. 지역 체크 (정책에 지역 제한이 있는 경우)
    user_residence = user_info.get('residence', '')
    if policy.district and user_residence:
        # 정책 지역과 사용자 지역이 일치하지 않으면 제외
        if policy.district not in user_residence and user_residence not in policy.district:
            return False

    # 3. 코드 필터 체크 (취업/학력/결혼)
    if not _passes_profile_code_filters(policy, user_info):
        return False

    # 4. 특수조건 체크 (한부모, 장애인, 수급자, 신혼, 중소기업, 군인 등)
    if not _check_special_conditions(policy, user_info):
        return False

    return True


def _get_relevant_categories(user_info):
    """
    사용자 맥락에서 관련 카테고리 도출

    [회의 결정사항 2026.01.19 반영]
    - 기존: 대분류(Categories M:N)만 사용
    - 변경: 중분류(subcategory) 키워드를 함께 반환하여 정밀 매칭 유도
    """
    relevant = []

    # 주거 맥락 → 중분류 키워드
    housing = user_info.get('housing_type', '')
    if housing:
        relevant.append('주거')  # 대분류

        # ---------------------------------------------------------------------
        # [2026.01.20] 중분류 키워드 수정 내역 (API 실제 값 반영)
        # ---------------------------------------------------------------------
        relevant.append('전월세 및 주거급여 지원')
        relevant.append('주택 및 거주지')

        if housing == '전세':
            relevant.append('전세')
        elif housing == '월세':
            relevant.append('월세')

    # 취업 맥락
    emp = user_info.get('employment_status', '')
    if emp in ['구직중', '무직']:
        relevant.append('일자리')  # 대분류

        # ---------------------------------------------------------------------
        # [2026.01.20] 중분류 키워드 수정 내역
        # ---------------------------------------------------------------------
        relevant.append('취업')
        relevant.append('창업')
        relevant.append('재직자')

    elif emp == '창업준비':
        relevant.append('창업')

    # 소득 맥락 (생활지원)
    income = user_info.get('income')
    if income is not None and income < 3600:
        # ---------------------------------------------------------------------
        # [2026.01.20] 대분류 변경 (생활 -> 복지문화)
        # ---------------------------------------------------------------------
        relevant.append('복지문화')  # 대분류
        relevant.append('취약계층 및 금융지원')

    # 특수조건 맥락
    special = user_info.get('special_conditions', [])
    if any(s in ['한부모', '장애'] for s in special):
        relevant.append('취약계층 및 금융지원')
        relevant.append('건강')  # 신규 추가

    # 자녀/학생 맥락
    if user_info.get('has_children') or user_info.get('children_ages'):
        relevant.append('교육')  # 대분류

        # ---------------------------------------------------------------------
        # [2026.01.20] 중분류 키워드 수정 내역
        # ---------------------------------------------------------------------
        relevant.append('교육비지원')

    # 문화/예술 관심
    if '예술' in user_info.get('interests', []):
        relevant.append('복지문화')
        relevant.append('문화활동')
        relevant.append('예술인지원')

    # 사용자가 직접 선택한 필요분야
    needs = user_info.get('needs', [])
    for need in needs:
        if need not in relevant:
            relevant.append(need)

    # 기본: 청년이면 일자리/주거 + 기본 중분류
    age = user_info.get('age')
    if not relevant and age and 19 <= age <= 39:
        relevant = ['주거', '일자리', '복지문화', '취업', '전월세 및 주거급여 지원']

    return relevant


# =============================================================================
# [BRAIN4-14] 점수 계산 - 신혼부부 청년 감점 로직 제거
# =============================================================================

def _calc_priority(policy, user_info, relevant_categories):
    """
    우선순위 점수 계산

    [BRAIN4-14 개선]
    - 기존: 신혼부부가 청년 정책에서 감점 (0점)
    - 개선: 청년/신혼 독립 적용, 둘 다 해당되면 둘 다 점수 받음
    """
    score = 0

    # 정책 텍스트 준비
    policy_name = policy.title.lower()  # [RENAME] plcy_nm → title
    description = (policy.description or '').lower()  # [RENAME] plcy_expln_cn → description
    support_content = (policy.support_content or '').lower()  # [RENAME] plcy_sprt_cn → support_content

    # 카테고리 (대분류 + 중분류)
    # 1. 대분류: M:N 관계 (기존 로직 유지)
    category_names = [c.name.lower() for c in policy.categories.all()]
    # 2. 중분류: Policy 모델의 subcategory 필드 사용
    mclsf = (policy.subcategory or '').lower()  # [RENAME] mclsf_nm → subcategory

    # 사용자 정보
    housing = user_info.get('housing_type', '')
    emp_status = user_info.get('employment_status', '')
    user_special = [s.lower() for s in user_info.get('special_conditions', [])]
    is_newlywed = any('신혼' in s for s in user_special)

    # =========================================================================
    # 1. 청년 특화 복지 - 신혼부부도 청년이면 동일 점수
    # =========================================================================
    if '청년' in policy_name:
        score += 30

    # =========================================================================
    # 2. 특수조건 매칭 보너스 (독립적으로 적용)
    # =========================================================================
    if is_newlywed and (policy.is_for_newlywed or '신혼' in policy_name or '신혼' in description):
        score += 50

    # 다른 특수조건도 동일하게 적용
    if any('한부모' in s for s in user_special) and policy.is_for_single_parent:
        score += 50
    if any('장애' in s for s in user_special) and policy.is_for_disabled:
        score += 50
    if any('수급' in s for s in user_special) and policy.is_for_low_income:
        score += 50

    # =========================================================================
    # 3. "우대" 정책 보너스 (전용 아닌 정책에서 해당 조건 언급 시)
    # =========================================================================
    policy_text = f"{description} {support_content}"
    for condition in user_special:
        if condition in policy_text:
            if any(kw in policy_text for kw in ['우대', '가점', '우선']):
                score += 15

    # 4. 실질적 금전 혜택 (지원내용에서 금액 파싱)
    amounts = re.findall(r'(\d+)만원', support_content)
    if amounts:
        max_amount = max([int(a) for a in amounts])
        if max_amount >= 100:
            score += 25
        elif max_amount >= 50:
            score += 15
        elif max_amount >= 10:
            score += 5

    # 5. 관련 카테고리 매칭 (중분류 우선 적용)
    for cat in relevant_categories:
        cat_lower = cat.lower()

        # [2026.01.19 반영] 중분류 매칭 시 가점 상향 (+30)
        # [2026.01.20 개선] 공백 무시 비교 (예: "주거 급여" vs "주거급여")
        if cat_lower.replace(" ", "") in mclsf.replace(" ", ""):
            score += 30

        # 기존 대분류 매칭 (+20)
        elif any(cat_lower in c for c in category_names):
            score += 20

        # 텍스트 단순 매칭 (+10)
        if cat_lower in description or cat_lower in policy_name:
            score += 10

    # 6. 주거형태 세부 매칭
    if housing:
        if housing == '월세':
            if '월세' in policy_name or '월세' in description:
                score += 40
            elif '전월세' in policy_name:
                score += 25
            elif '전세' in policy_name and '월세' not in policy_name:
                score -= 30
        elif housing == '전세':
            if '전세' in policy_name or '전세' in description:
                score += 40
            elif '전월세' in policy_name:
                score += 25
            elif '월세' in policy_name and '전세' not in policy_name:
                score -= 30

    # 7. 고용상태 세부 매칭
    if emp_status in ['구직중', '무직']:
        if any(kw in policy_name for kw in ['취업', '일자리', '자립']):
            score += 20
        if any(kw in policy_name for kw in ['청년통장', '저축']):
            score += 20

    # 8. 핵심 키워드 보너스
    core_keywords = ['자립', '통장', '지원금', '수당', '월세']
    for kw in core_keywords:
        if kw in policy_name:
            score += 10

    return score


def _select_diverse_categories(scored_policies, max_per_category=2, limit=None):
    """
    카테고리별로 골고루 선택 (다양성 보장)

    [회의 결정사항 2026.01.19 반영]
    - 기존: 대분류(Categories) 기준으로만 분산
    - 변경: 중분류(subcategory)가 있으면 중분류 기준으로 분산 선택

    [BRAIN4-31] 변경사항:
    - limit=None 처리 추가: 전체 반환 시 max_per_category 제한만 적용
    - 회원 웹용(match_policies_for_web)에서 전체 정책 반환 지원
    - max_per_category=None 처리: 카테고리 제한 없이 점수순 반환
    """
    final_results = []
    categories_selected = {}

    # [BRAIN4-31] limit이 None이면 전체 반환 (max_per_category 제한만 적용)
    effective_limit = limit if limit is not None else len(scored_policies)

    for policy, score in scored_policies:
        # 중분류 우선 사용, 없으면 대분류 사용
        cat_name = policy.subcategory or policy.category or '기타'  # [RENAME] mclsf_nm → subcategory, lclsf_nm → category

        if max_per_category is None or categories_selected.get(cat_name, 0) < max_per_category:
            final_results.append((policy, score))
            categories_selected[cat_name] = categories_selected.get(cat_name, 0) + 1

        if len(final_results) >= effective_limit:
            break

    return final_results
