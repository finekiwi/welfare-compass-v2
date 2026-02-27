from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework.pagination import PageNumberPagination
from django.core.paginator import Paginator, EmptyPage
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, timedelta
from .models import Policy, Category, MapPOI
from .serializers import PolicyListSerializer, PolicyDetailSerializer, CategorySerializer, MapPOISerializer
# [BRAIN4-31] 회원용/챗봇용 분리
from .services.matching import match_policies_for_web
from .services.youth_api import get_youth_centers  # [BRAIN4-Map] 온통청년 API 서비스


class StandardResultsSetPagination(PageNumberPagination):
    """
    표준 페이지네이션 클래스
    - 기본 12개 (프론트엔드 디자인 기준)
    - page_size 쿼리 파라미터로 클라이언트에서 제어 가능 (최대 100개)
    """
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100


class PolicyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    정책 조회 API
    - GET /api/policies/          : 목록
    - GET /api/policies/{policy_id}/ : 상세
    - GET /api/policies/deadline_soon/ : 마감임박
    - GET /api/policies/recommended/ : 맞춤추천
    """
    queryset = Policy.objects.prefetch_related('categories').all()
    pagination_class = StandardResultsSetPagination

    # 필터링/검색/정렬 추가
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['district', 'categories__name']  # 필터 가능한 필드
    search_fields = ['title', 'description']  # [RENAME] plcy_nm → title, plcy_expln_cn → description
    ordering_fields = ['apply_end_date', 'created_at']  # [RENAME] aply_end_dt → apply_end_date, frst_reg_dt → created_at
    ordering = ['-created_at']  # [RENAME] -frst_reg_dt → -created_at (기본 정렬: 최신순)

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # [BRAIN4-36] 프론트엔드 카테고리 필터링
        # 홈 화면에서 category=housing 등의 키로 요청이 오면 매핑된 필터 적용
        category_key = self.request.query_params.get('category')
        if category_key:
            from .constants import FRONTEND_CATEGORY_MAP
            if category_key in FRONTEND_CATEGORY_MAP:
                queryset = queryset.filter(FRONTEND_CATEGORY_MAP[category_key])
            else:
                # 기존 동작: 대분류 이름(예: '주거')으로 필터링
                # (categories__name 필터는 DjangoFilterBackend가 처리하지만,
                #  여기서 명시적으로 처리할 수도 있음. 일단 둠)
                pass
                
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return PolicyListSerializer
        return PolicyDetailSerializer

    @action(detail=False, methods=['get'])
    def deadline_soon(self, request):
        """마감임박 정책 (7일 이내, 최대 6개)"""
        today = date.today()
        week_later = today + timedelta(days=7)

        # [BRAIN4-36] 카테고리 필터링 지원
        queryset = self.get_queryset() # get_queryset 호출하여 필터 적용

        policies = queryset.filter(
            apply_end_date__gte=today,  # [RENAME] aply_end_dt → apply_end_date
            apply_end_date__lte=week_later  # [RENAME] aply_end_dt → apply_end_date
        ).order_by('apply_end_date')[:6]  # [RENAME] aply_end_dt → apply_end_date

        serializer = PolicyListSerializer(policies, many=True)
        return Response(serializer.data)

    # =========================================================================
    # [BRAIN4-19] 달력용 API
    # =========================================================================
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """
        달력 이벤트 목록 API

        Query Params:
        - year: 연도 (기본: 현재 연도)
        - month: 월 (기본: 현재 월)
        - mode: 'apply' (신청기간) 또는 'biz' (사업기간), 기본: 'apply'

        Returns:
        - events: 해당 월에 해당하는 정책 목록 (날짜 데이터 포함)
        """
        from .serializers import CalendarEventSerializer
        from django.db.models import Q

        # 파라미터 파싱
        today = date.today()
        year = int(request.query_params.get('year', today.year))
        month = int(request.query_params.get('month', today.month))
        mode = request.query_params.get('mode', 'apply')

        # 해당 월의 시작일/종료일
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        # 모드에 따라 필터링
        if mode == 'biz':
            # 사업기간 기준: 해당 월과 겹치는 정책
            policies = Policy.objects.filter(
                business_start_date__isnull=False,  # [RENAME] biz_prd_bgng_ymd → business_start_date
                business_end_date__isnull=False  # [RENAME] biz_prd_end_ymd → business_end_date
            ).filter(
                Q(business_start_date__lte=month_end) & Q(business_end_date__gte=month_start)  # [RENAME]
            )
        else:
            # 신청기간 기준 (기본): 해당 월과 겹치는 정책
            policies = Policy.objects.filter(
                apply_start_date__isnull=False,  # [RENAME] aply_start_dt → apply_start_date
                apply_end_date__isnull=False  # [RENAME] aply_end_dt → apply_end_date
            ).filter(
                Q(apply_start_date__lte=month_end) & Q(apply_end_date__gte=month_start)  # [RENAME]
            )

        serializer = CalendarEventSerializer(policies, many=True)

        return Response({
            'year': year,
            'month': month,
            'mode': mode,
            'count': policies.count(),
            'events': serializer.data
        })

    # =========================================================================
    # [BRAIN4-14] 맞춤추천 API
    # [BRAIN4-31] match_policies_for_web() 사용으로 변경
    # =========================================================================
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def recommended(self, request):
        """
        프로필 기반 맞춤 정책 추천

        [BRAIN4-34] 변경사항:
        - limit 파라미터 제거, 전체 반환 (프론트엔드 페이지네이션 처리를 위해) -> [BRAIN4-35] 백엔드 페이지네이션 지원

        Query Params:
            - category: 특정 카테고리 필터 (선택)
            - exclude: 제외할 정책 ID들, 콤마 구분 (선택)
            - page: 페이지 번호 (기본 1)
            - page_size: 페이지 크기 (기본 12)
        """
        profile = request.user.profile

        # 프로필 완성도 체크
        if not profile.birth_year:
            return Response({
                "error": "프로필을 먼저 완성해주세요.",
                "code": "PROFILE_INCOMPLETE",
                "required_fields": ["birth_year"]
            }, status=400)

        # Query params
        category = request.query_params.get('category')
        exclude_str = request.query_params.get('exclude', '')
        exclude_ids = [x.strip() for x in exclude_str.split(',') if x.strip()]

        # 페이지네이션 파라미터 (잘못된 값 방어)
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = max(1, min(int(request.query_params.get('page_size', 12)), 100))
        except (ValueError, TypeError):
            page_size = 12

        # [BRAIN4-31] 전체 정책 매칭 (점수순 정렬됨)
        results = match_policies_for_web(
            profile=profile,
            exclude_policy_ids=exclude_ids if exclude_ids else None,
            include_category=category,
        )

        # [BRAIN4-35] 서버 사이드 페이지네이션 적용 (Manual slicing using Paginator)
        paginator = Paginator(results, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = [] # 페이지 초과 시 빈 리스트
            
        if isinstance(page_obj, list):
             current_page_items = []
        else:
            current_page_items = page_obj.object_list

        # 응답 구성
        policies_to_serialize = [p for p, score in current_page_items]
        scores = {p.policy_id: score for p, score in current_page_items}  # [RENAME] plcy_no → policy_id

        serializer = PolicyListSerializer(policies_to_serialize, many=True)

        # 각 정책에 점수 추가
        data = serializer.data
        for item in data:
            item['match_score'] = scores.get(item['plcy_no'], 0)  # API 응답은 plcy_no, 내부는 policy_id
        
        # Profile Summary 구성
        profile_summary = {
            "age": profile.age,
            "district": profile.district or "미설정",
            "housing_type": profile.get_housing_type_display() if profile.housing_type else "미설정",
            "job_status": profile.get_job_status_display() if profile.job_status else "미설정",
            "interests": list(profile.interests.values_list('name', flat=True)),
            "special_conditions": profile.special_conditions or [],
        }

        return Response({
            "count": paginator.count,
            "profile_summary": profile_summary,
            "results": data
        })


class CenterViewSet(viewsets.ViewSet):
    """
    청년센터/공간 조회 API (온통청년 API 연동)
    - GET /api/centers/
    """
    throttle_classes = [AnonRateThrottle]  # [FIX] 외부 API rate limit 방어

    def list(self, request):
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = max(1, min(int(request.query_params.get('page_size', 10)), 100))
        except (ValueError, TypeError):
            page_size = 10

        # 온통청년 API 호출
        data = get_youth_centers(page=page, size=page_size)
        
        # 외부 API라 total count를 정확히 알기 어려울 수 있음 (API 응답에 따라 다름)
        # 일단 리스트 반환. 필요시 포맷팅.
        return Response({
            "page": page,
            "page_size": page_size,
            "results": data
        })


class MapPOIViewSet(viewsets.ReadOnlyModelViewSet):
    """
    지도 POI 조회 API
    - GET /api/policies/map/pois/
    - GET /api/policies/map/pois/?theme_id=...
    """
    queryset = MapPOI.objects.select_related('theme').all()
    serializer_class = MapPOISerializer
    pagination_class = None  # 지도는 한 번에 다 불러오는 경우가 많음 (또는 클라이언트 사이드 클러스터링)

    def get_queryset(self):
        queryset = super().get_queryset()
        theme_id = self.request.query_params.get('theme_id')
        if theme_id:
            queryset = queryset.filter(theme__theme_id=theme_id)
        return queryset
