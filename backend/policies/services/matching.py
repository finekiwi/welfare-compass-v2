"""
정책 매칭 서비스 - Django 모델 기반

[BRAIN4-14] 버그 수정 내역:
1. 특수조건 필터링: 텍스트 파싱 → API 코드 기반 Boolean 필드
2. 점수 계산: 신혼부부 청년 감점 로직 제거
"""
import re
from django.db.models import Q
from policies.models import Policy


def match_policies(profile, exclude_policy_ids=None, include_category=None, limit=10):
    """
    사용자 프로필에 맞는 정책 매칭
    
    Args:
        profile: accounts.Profile 인스턴스
        exclude_policy_ids: 제외할 정책 ID 리스트
        include_category: 특정 카테고리만 포함
        limit: 최대 반환 개수
    
    Returns:
        list of (Policy, score) tuples
    """
    user_info = profile.to_matching_dict()
    
    # Step 1: Django ORM으로 기본 필터링
    queryset = _apply_base_filters(user_info, exclude_policy_ids, include_category)
    
    # Step 2: 정책 리스트 가져오기
    policies = list(queryset.prefetch_related('categories'))
    
    # Step 3: 특수조건 필터링 (Boolean 필드 기반)
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
    final_results = _select_diverse_categories(scored_policies, max_per_category=2, limit=limit)
    
    return final_results


def _apply_base_filters(user_info, exclude_policy_ids, include_category):
    """Django ORM으로 기본 필터 적용"""
    queryset = Policy.objects.all()
    
    # 제외할 정책
    if exclude_policy_ids:
        queryset = queryset.exclude(plcy_no__in=exclude_policy_ids)
    
    # 특정 카테고리만
    if include_category:
        queryset = queryset.filter(categories__name__icontains=include_category)
    
    # 나이 필터
    age = user_info.get('age')
    if age:
        queryset = queryset.filter(
            Q(sprt_trgt_min_age__isnull=True) | Q(sprt_trgt_min_age__lte=age),
            Q(sprt_trgt_max_age__isnull=True) | Q(sprt_trgt_max_age__gte=age)
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
    
    return queryset.distinct()


# =============================================================================
# [BRAIN4-14] 특수조건 필터링 - 텍스트 파싱 → Boolean 필드 기반
# =============================================================================
#
# ❌ BEFORE: 텍스트에 키워드만 있으면 무조건 제외 (우대/가점도 제외됨)
# -----------------------------------------------------------------------------
# def _check_special_conditions(policy, user_info):
#     policy_text = f"{policy.plcy_expln_cn or ''} {policy.plcy_sprt_cn or ''}".lower()
#     user_special = [s.lower() for s in user_info.get('special_conditions', [])]
#     
#     # 문제: "신혼부부 우대" 정책도 제외됨!
#     if '신혼' in policy_text:
#         if not any('신혼' in s for s in user_special):
#             return False  # 일반 청년도 지원 가능한데 제외
#     
#     if '한부모' in policy_text:
#         if not any('한부모' in s for s in user_special):
#             return False
#     ...
# -----------------------------------------------------------------------------
#
# ✅ AFTER: API sbizCd 기반 Boolean 필드로 "전용"만 제외
# - 한부모(0014004), 장애인(0014005), 기초수급자(0014003)는 API 코드 기반
# - 신혼부부는 API 코드 없어서 텍스트 파싱하되 "전용" 패턴만 체크
# =============================================================================

def _check_special_conditions(policy, user_info):
    """
    특수조건 체크 - Policy 모델의 Boolean 필드 기반
    
    [BRAIN4-14 개선]
    - 기존: 텍스트에 "신혼" 있으면 무조건 제외 → "우대" 정책도 제외되는 버그
    - 개선: ETL에서 "전용" 여부를 Boolean 필드로 저장 → 정확한 필터링
    """
    user_special = [s.lower() for s in user_info.get('special_conditions', [])]
    
    # 한부모 전용 정책 (sbizCd: 0014004)
    if policy.is_for_single_parent:
        if not any('한부모' in s for s in user_special):
            return False
    
    # 장애인 전용 정책 (sbizCd: 0014005)
    if policy.is_for_disabled:
        if not any(s in ['장애', '장애인'] for s in user_special):
            return False
    
    # 기초수급자 전용 정책 (sbizCd: 0014003)
    if policy.is_for_low_income:
        if not any(s in ['기초수급', '기초수급자', '수급자'] for s in user_special):
            return False
    
    # 신혼부부 전용 정책 (텍스트 파싱 - API 코드 없음)
    if policy.is_for_newlywed:
        if not any('신혼' in s for s in user_special):
            return False
    
    # 1인가구 체크 (별도 Boolean 필드 없음 - 텍스트 기반 유지)
    policy_text = f"{policy.plcy_expln_cn or ''} {policy.plcy_sprt_cn or ''}"
    if '1인가구 전용' in policy_text or '1인가구만' in policy_text:
        household_size = user_info.get('household_size')
        if household_size and household_size != 1:
            return False
    
    return True


def _get_relevant_categories(user_info):
    """사용자 맥락에서 관련 카테고리 도출"""
    relevant = []
    
    # 주거 맥락
    housing = user_info.get('housing_type', '')
    if housing:
        relevant.append('주거')
        if housing == '전세':
            relevant.append('전세')
        elif housing == '월세':
            relevant.append('월세')
    
    # 취업 맥락
    emp = user_info.get('employment_status', '')
    if emp in ['구직중', '무직']:
        relevant.append('일자리')
    
    # 소득 맥락
    income = user_info.get('income')
    if income is not None and income < 300:
        relevant.append('생활')
        relevant.append('금융')
    
    # 특수조건 맥락
    special = user_info.get('special_conditions', [])
    if any(s in ['한부모', '장애인', '장애'] for s in special):
        relevant.append('생활')
    
    # 자녀 맥락
    if user_info.get('has_children') or user_info.get('children_ages'):
        relevant.append('교육')
    
    # 사용자가 직접 선택한 필요분야
    needs = user_info.get('needs', [])
    for need in needs:
        if need not in relevant:
            relevant.append(need)
    
    # 기본: 청년이면 일자리/주거
    age = user_info.get('age')
    if not relevant and age and 19 <= age <= 39:
        relevant = ['주거', '일자리', '생활']
    
    return relevant


# =============================================================================
# [BRAIN4-14] 점수 계산 - 신혼부부 청년 감점 로직 제거
# =============================================================================
#
# ❌ BEFORE: 신혼부부가 청년 정책에서 감점됨
# -----------------------------------------------------------------------------
# if '청년' in policy_name:
#     if is_newlywed:
#         score += 10   # 왜 낮음? 신혼부부도 청년인데
#     else:
#         score += 30
# 
# if is_newlywed:
#     if '청년' in policy_name and '신혼' not in policy_name:
#         score -= 10   # 또 감점?? 
#
# 결과: 신혼 청년 = 10 - 10 = 0점, 일반 청년 = 30점 → 불합리
# -----------------------------------------------------------------------------
#
# ✅ AFTER: 청년 여부와 신혼 여부는 독립적인 속성
# - 청년이면 +30 (신혼 여부 무관)
# - 신혼이고 신혼 정책이면 +50 (별도 보너스)
# - 둘 다 해당되면 둘 다 받음 (30 + 50 = 80)
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
    policy_name = policy.plcy_nm.lower()
    description = (policy.plcy_expln_cn or '').lower()
    support_content = (policy.plcy_sprt_cn or '').lower()
    
    # 카테고리 이름들
    category_names = [c.name.lower() for c in policy.categories.all()]
    
    # 사용자 정보
    housing = user_info.get('housing_type', '')
    emp_status = user_info.get('employment_status', '')
    user_special = [s.lower() for s in user_info.get('special_conditions', [])]
    is_newlywed = any('신혼' in s for s in user_special)
    
    # =========================================================================
    # 1. 청년 특화 복지 - 신혼부부도 청년이면 동일 점수
    # =========================================================================
    # BEFORE: if is_newlywed: score += 10 else: score += 30
    # AFTER:  청년이면 무조건 30점
    if '청년' in policy_name:
        score += 30
    
    # =========================================================================
    # 2. 특수조건 매칭 보너스 (독립적으로 적용)
    # =========================================================================
    # BEFORE: 청년 정책에서 신혼부부 감점 (-10)
    # AFTER:  감점 없음, 신혼 정책 매칭 시 보너스만 추가
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
    
    # 5. 관련 카테고리 매칭
    for cat in relevant_categories:
        cat_lower = cat.lower()
        if any(cat_lower in c for c in category_names):
            score += 20
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


def _select_diverse_categories(scored_policies, max_per_category=2, limit=10):
    """카테고리별로 골고루 선택"""
    final_results = []
    categories_selected = {}
    
    for policy, score in scored_policies:
        # 첫 번째 카테고리를 기준으로
        categories = list(policy.categories.all())
        cat_name = categories[0].name if categories else '기타'
        
        if categories_selected.get(cat_name, 0) < max_per_category:
            final_results.append((policy, score))
            categories_selected[cat_name] = categories_selected.get(cat_name, 0) + 1
        
        if len(final_results) >= limit:
            break
    
    return final_results
