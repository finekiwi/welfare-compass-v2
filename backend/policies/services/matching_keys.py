"""
매칭 키/코드 매핑 단일 소스 (Single Source of Truth)

[BRAIN4-34] 신규 파일
- 매칭 dict 키 계약
- 특수조건 canonical 값 및 alias 매핑
- 취업/학력/결혼/주거 코드 매핑
- API 제한없음 코드, sbizCd 코드 상수
- 정규화 함수
"""

# =============================================================================
# 매칭 Dict 키 계약
# Profile.to_matching_dict()가 반환해야 하는 키 집합
# =============================================================================

MATCHING_DICT_KEYS = frozenset({
    'age',
    'residence',
    'employment_status',
    'job_code',
    'education_code',
    'marriage_code',
    'housing_type',
    'income',
    'household_size',
    'has_children',
    'children_ages',
    'special_conditions',
    'needs',
    'interests',
})


# =============================================================================
# 특수조건 (Special Conditions)
# =============================================================================

VALID_SPECIAL_CONDITIONS = [
    '신혼', '한부모', '장애', '다자녀', '저소득', '차상위', '기초수급',
    '중소기업', '군인',
]

SPECIAL_CONDITION_ALIASES = {
    '장애인': '장애',
    '기초수급자': '기초수급',
    '수급자': '기초수급',
}


# =============================================================================
# 취업상태 코드 매핑
# Profile.job_status → API jobCd / 한글
# =============================================================================

JOB_STATUS_TO_CODE = {
    'employed': '0013001',       # 재직자
    'self_employed': '0013002',  # 자영업자
    'unemployed': '0013003',     # 미취업자
    'job_seeking': '0013003',    # 구직중 → 미취업자
    'student': '0013003',        # 학생 → 미취업자 (API에 학생 코드 없음)
    'startup': '0013006',        # (예비)창업자
    'freelancer': '0013004',     # 프리랜서
}

JOB_STATUS_TO_KOREAN = {
    'employed': '재직',
    'self_employed': '자영업',
    'unemployed': '무직',
    'job_seeking': '구직중',
    'student': '학생',
    'startup': '창업준비',
    'freelancer': '프리랜서',
}


# =============================================================================
# 학력상태 코드 매핑
# Profile.education_status → API schoolCd
# =============================================================================

EDUCATION_STATUS_TO_CODE = {
    'below_high_school': '0049001',      # 고졸 미만
    'high_school_enrolled': '0049002',   # 고교 재학
    'high_school': '0049004',            # 고교 졸업
    'university_enrolled': '0049005',    # 대학 재학
    'university_leave': '0049005',       # 대학 휴학 → 대학 재학
    'university': '0049007',             # 대학 졸업
    'graduate_school': '0049008',        # 석박사
}

# 학력 문자열 입력(챗봇/수동 dict 입력) → 코드 정규화
# 회의 결정 반영: 고3→고졸예정(0049003), 대4→대졸예정(0049006)
EDUCATION_LABEL_TO_CODE = {
    '고졸 미만': '0049001',
    '고교 재학': '0049002',
    '고3': '0049003',
    '고졸예정': '0049003',
    '고졸 예정': '0049003',
    '고졸': '0049004',
    '대학 재학': '0049005',
    '대4': '0049006',
    '대졸예정': '0049006',
    '대졸 예정': '0049006',
    '대졸': '0049007',
    '석박사': '0049008',
}

# 학력 추가 매칭: 사용자 코드 → 추가로 매칭해야 할 정책 코드
# 고교 재학(0049002) → 고졸예정(0049003) 정책도 매칭
# 대학 재학(0049005) → 대졸예정(0049006) 정책도 매칭
EDUCATION_ALSO_MATCH = {
    '0049002': ['0049003'],  # 고교 재학 → 고졸예정
    '0049005': ['0049006'],  # 대학 재학 → 대졸예정
}


# =============================================================================
# 결혼상태 코드 매핑
# Profile.marriage_status → API mrgSttsCd
# =============================================================================

MARRIAGE_STATUS_TO_CODE = {
    'married': '0055001',  # 기혼
    'single': '0055002',   # 미혼
}


# =============================================================================
# 주거형태 한글 매핑 (점수 계산용)
# =============================================================================

HOUSING_TYPE_TO_KOREAN = {
    'jeonse': '전세',
    'monthly': '월세',
    'owned': '자가',
    # 레거시 하위 호환 (마이그레이션 전 DB 값)
    'gosiwon': '월세',
    'parents': '자가',
    'public': '월세',
    'other': '',
}


# =============================================================================
# API 제한없음 코드 (정책 필터링 시 "조건 없음" 판별)
# =============================================================================

RESTRICTION_CODE_JOB = '0013010'         # 취업상태 제한없음
RESTRICTION_CODE_EDUCATION = '0049010'   # 학력 제한없음
RESTRICTION_CODE_MARRIAGE = '0055003'    # 결혼상태 제한없음


# =============================================================================
# sbizCd 코드 상수 (특수조건)
# =============================================================================

SBIZ_CODE_SME = '0014001'             # 중소기업
SBIZ_CODE_LOW_INCOME = '0014003'      # 기초수급자
SBIZ_CODE_SINGLE_PARENT = '0014004'   # 한부모
SBIZ_CODE_DISABLED = '0014005'        # 장애인
SBIZ_CODE_MILITARY = '0014007'        # 군인


# =============================================================================
# 반환 계약
# =============================================================================

CHATBOT_TOP_K = 2  # 챗봇은 상위 2개 고정 반환


# =============================================================================
# 정규화 함수
# =============================================================================

def normalize_special_conditions(values: list[str]) -> list[str]:
    """
    특수조건 리스트를 canonical 형태로 정규화.
    - alias 적용 (장애인→장애, 기초수급자→기초수급, 수급자→기초수급)
    - 중복 제거 (첫 등장 순서 유지)
    """
    seen = set()
    result = []
    for v in values:
        canonical = SPECIAL_CONDITION_ALIASES.get(v.strip(), v.strip())
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def normalize_user_info(user_info: dict) -> dict:
    """
    user_info dict의 special_conditions를 정규화.
    원본을 변경하지 않고 새 dict 반환.
    """
    normalized = dict(user_info)

    # 학력 코드 정규화
    # 1) education_code가 문자열 라벨/enum이면 코드로 변환
    # 2) education_status만 들어온 경우 education_code를 보강
    raw_education_code = normalized.get('education_code')
    if raw_education_code:
        raw = str(raw_education_code).strip()
        normalized['education_code'] = (
            EDUCATION_LABEL_TO_CODE.get(raw) or
            EDUCATION_STATUS_TO_CODE.get(raw) or
            raw
        )
    else:
        raw_education_status = normalized.get('education_status')
        if raw_education_status:
            raw = str(raw_education_status).strip()
            mapped = (
                EDUCATION_LABEL_TO_CODE.get(raw) or
                EDUCATION_STATUS_TO_CODE.get(raw)
            )
            if mapped:
                normalized['education_code'] = mapped

    raw_conditions = normalized.get('special_conditions', [])
    if raw_conditions:
        normalized['special_conditions'] = normalize_special_conditions(raw_conditions)
    return normalized


# =============================================================================
# Known 코드 집합 (unknown 판별 기준)
# =============================================================================

KNOWN_EDUCATION_CODES: set[str] = {
    '0049001', '0049002', '0049003', '0049004',
    '0049005', '0049006', '0049007', '0049008', '0049010',
}

KNOWN_JOB_CODES: set[str] = {
    '0013001', '0013002', '0013003', '0013004', '0013006', '0013010',
}


# =============================================================================
# 코드 문자열 파싱 유틸
# =============================================================================

def parse_code_string(raw: str | None) -> set[str]:
    """'0013001, 0013003' -> {'0013001', '0013003'}"""
    if raw is None:
        return set()

    tokens: set[str] = set()
    for part in str(raw).split(','):
        code = part.strip()
        if not code:
            continue

        # 범위 표현 방어: 0013001~0013009
        if '~' in code:
            s, e = [x.strip() for x in code.split('~', 1)]
            if s.isdigit() and e.isdigit() and len(s) == len(e) and int(s) <= int(e):
                width = len(s)
                tokens.update(f"{n:0{width}d}" for n in range(int(s), int(e) + 1))
                continue

        tokens.add(code)

    return tokens


def has_unknown_codes(raw: str | None, known: set[str]) -> bool:
    """unknown 코드가 1개라도 있으면 True"""
    codes = parse_code_string(raw)
    return bool(codes - known)


def extract_known_only(raw: str | None, known: set[str]) -> str:
    """unknown 제거 후 known 코드만 ','로 join한 문자열 반환"""
    codes = parse_code_string(raw)
    known_codes = sorted(codes & known, key=int)
    return ','.join(known_codes)
