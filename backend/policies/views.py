from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, timedelta
from .models import Policy, Category
from .serializers import PolicyListSerializer, PolicyDetailSerializer, CategorySerializer
# [BRAIN4-31] 회원용/챗봇용 분리
from .services.matching import match_policies_for_web


class PolicyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    정책 조회 API
    - GET /api/policies/          : 목록
    - GET /api/policies/{policy_id}/ : 상세
    - GET /api/policies/deadline_soon/ : 마감임박
    - GET /api/policies/recommended/ : 맞춤추천
    """
    queryset = Policy.objects.prefetch_related('categories').all()

    # 필터링/검색/정렬 추가
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['district', 'categories__name']  # 필터 가능한 필드
    search_fields = ['title', 'description']  # [RENAME] plcy_nm → title, plcy_expln_cn → description
    ordering_fields = ['apply_end_date', 'created_at']  # [RENAME] aply_end_dt → apply_end_date, frst_reg_dt → created_at
    ordering = ['-created_at']  # [RENAME] -frst_reg_dt → -created_at (기본 정렬: 최신순)

    def get_serializer_class(self):
        if self.action == 'list':
            return PolicyListSerializer
        return PolicyDetailSerializer

    @action(detail=False, methods=['get'])
    def deadline_soon(self, request):
        """마감임박 정책 (7일 이내, 최대 6개)"""
        today = date.today()
        week_later = today + timedelta(days=7)

        policies = Policy.objects.filter(
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
        - limit 파라미터 제거, 전체 반환 (프론트엔드 페이지네이션 처리)

        Query Params:
            - category: 특정 카테고리 필터 (선택)
            - exclude: 제외할 정책 ID들, 콤마 구분 (선택)
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

        # [BRAIN4-34] 전체 정책 반환 (프론트에서 페이지네이션 처리)
        results = match_policies_for_web(
            profile=profile,
            exclude_policy_ids=exclude_ids if exclude_ids else None,
            include_category=category,
        )

        # 응답 구성
        policies = [p for p, score in results]
        scores = {p.policy_id: score for p, score in results}  # [RENAME] plcy_no → policy_id

        serializer = PolicyListSerializer(policies, many=True)

        # 각 정책에 점수 추가
        data = serializer.data
        for item in data:
            item['match_score'] = scores.get(item['plcy_no'], 0)  # API 응답은 plcy_no, 내부는 policy_id

        return Response({
            "count": len(data),
            "profile_summary": {
                "age": profile.age,
                "district": profile.district or "미설정",
                "housing_type": profile.get_housing_type_display() if profile.housing_type else "미설정",
                "job_status": profile.get_job_status_display() if profile.job_status else "미설정",
                "interests": list(profile.interests.values_list('name', flat=True)),
                "special_conditions": profile.special_conditions or [],
            },
            "results": data
        })
