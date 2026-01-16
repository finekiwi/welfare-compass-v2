from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, timedelta
from .models import Policy, Category
from .serializers import PolicyListSerializer, PolicyDetailSerializer, CategorySerializer


class PolicyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    정책 조회 API
    - GET /api/policies/          : 목록
    - GET /api/policies/{plcy_no}/ : 상세
    """
    queryset = Policy.objects.prefetch_related('categories').all()

    # 필터링/검색/정렬 추가
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['district', 'categories__name']  # 필터 가능한 필드
    search_fields = ['plcy_nm', 'plcy_expln_cn']         # 검색 가능한 필드
    ordering_fields = ['aply_end_dt', 'frst_reg_dt']     # 정렬 가능한 필드
    ordering = ['-frst_reg_dt']                          # 기본 정렬: 최신순
    
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
            aply_end_dt__gte=today,
            aply_end_dt__lte=week_later
        ).order_by('aply_end_dt')[:6]
        
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
                biz_prd_bgng_ymd__isnull=False,
                biz_prd_end_ymd__isnull=False
            ).filter(
                Q(biz_prd_bgng_ymd__lte=month_end) & Q(biz_prd_end_ymd__gte=month_start)
            )
        else:
            # 신청기간 기준 (기본): 해당 월과 겹치는 정책
            policies = Policy.objects.filter(
                aply_start_dt__isnull=False,
                aply_end_dt__isnull=False
            ).filter(
                Q(aply_start_dt__lte=month_end) & Q(aply_end_dt__gte=month_start)
            )
        
        serializer = CalendarEventSerializer(policies, many=True)
        
        return Response({
            'year': year,
            'month': month,
            'mode': mode,
            'count': policies.count(),
            'events': serializer.data
        })