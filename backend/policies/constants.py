from django.db.models import Q

# 프론트엔드 카테고리(home.types.ts) -> 백엔드 필터 매핑
# 키: frontend category key
# 값: Django Q object for filtering Policy model
FRONTEND_CATEGORY_MAP = {
    'job': Q(category__in=['일자리']),
    'housing': Q(category__in=['주거']),
    'education': Q(category__in=['교육']),
    'welfare': Q(category__in=['복지문화', '복지', '문화', '금융']),
    'participation': Q(category__in=['참여권리', '참여', '권리']),
}

# [참고] 백엔드에 저장된 실제 lclsfNm (category):
# {'복지문화', '참여권리', '주거', '일자리', '교육'}
#
# 백엔드에 저장된 실제 mclsfNm (subcategory):
# {'건강', '교육비지원', '권익보호', '기숙사', '문화활동', '미래역량강화', '예술인지원', '온라인교육',
#  '재직자', '전월세 및 주거급여 지원', '정책인프라구축', '주택 및 거주지', '창업', '청년국제교류',
#  '청년참여', '취약계층 및 금융지원', '취업'}
