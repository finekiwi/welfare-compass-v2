"""
정책 매칭 서비스 - matching.py 로직을 Django 모델에 맞게 포팅
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
    
    # Step 3: 특수조건 필터링 (Python)
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


def _check_special_conditions(policy, user_info):
    """특수조건 체크 - 정책의 특수조건과 사용자 조건 매칭"""
    # Policy 모델에 special_conditions 필드가 없으므로
    # plcy_sprt_cn(지원내용)이나 plcy_expln_cn(설명)에서 키워드 체크
    
    policy_text = f"{policy.plcy_expln_cn or ''} {policy.plcy_sprt_cn or ''}".lower()
    user_special = [s.lower() for s in user_info.get('special_conditions', [])]
    
    # 신혼부부 전용 정책 체크
    if '신혼' in policy_text:
        if not any('신혼' in s for s in user_special):
            return False
    
    # 한부모 전용 정책 체크
    if '한부모' in policy_text:
        if not any('한부모' in s for s in user_special):
            return False
    
    # 장애인 전용 정책 체크
    if '장애' in policy_text:
        if not any('장애' in s for s in user_special):
            return False
    
    # 다자녀 전용 정책 체크
    if '다자녀' in policy_text:
        if not any('다자녀' in s for s in user_special):
            return False
    
    # 1인가구 전용
    if '1인' in policy_text or '1인가구' in policy_text:
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


def _calc_priority(policy, user_info, relevant_categories):
    """우선순위 점수 계산"""
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
    
    # 1. 청년 특화 복지
    if '청년' in policy_name:
        if is_newlywed:
            score += 10
        else:
            score += 30
    
    # 2. 신혼부부 우선
    if is_newlywed:
        if '신혼' in policy_name or '신혼' in description:
            score += 60
        if '청년' in policy_name and '신혼' not in policy_name:
            score -= 10
    
    # 3. 실질적 금전 혜택 (지원내용에서 금액 파싱)
    amounts = re.findall(r'(\d+)만원', support_content)
    if amounts:
        max_amount = max([int(a) for a in amounts])
        if max_amount >= 100:
            score += 25
        elif max_amount >= 50:
            score += 15
        elif max_amount >= 10:
            score += 5
    
    # 4. 관련 카테고리 매칭
    for cat in relevant_categories:
        cat_lower = cat.lower()
        if any(cat_lower in c for c in category_names):
            score += 20
        if cat_lower in description or cat_lower in policy_name:
            score += 10
    
    # 5. 주거형태 세부 매칭
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
    
    # 6. 고용상태 세부 매칭
    if emp_status in ['구직중', '무직']:
        if any(kw in policy_name for kw in ['취업', '일자리', '자립']):
            score += 20
        if any(kw in policy_name for kw in ['청년통장', '저축']):
            score += 20
    
    # 7. 핵심 키워드 보너스
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
