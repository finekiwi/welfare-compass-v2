from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, timedelta
from .models import Policy, Category
from .serializers import PolicyListSerializer, PolicyDetailSerializer, CategorySerializer
from .services.matching import match_policies


class PolicyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    정책 조회 API
    - GET /api/policies/          : 목록
    - GET /api/policies/{plcy_no}/ : 상세
    - GET /api/policies/deadline_soon/ : 마감임박
    - GET /api/policies/recommended/ : 맞춤추천
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def recommended(self, request):
        """
        프로필 기반 맞춤 정책 추천
        
        Query Params:
            - category: 특정 카테고리 필터 (선택)
            - exclude: 제외할 정책 ID들, 콤마 구분 (선택)
            - limit: 최대 개수 (기본 10, 최대 20)
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
        limit = min(int(request.query_params.get('limit', 10)), 20)
        
        # 매칭 실행
        results = match_policies(
            profile=profile,
            exclude_policy_ids=exclude_ids if exclude_ids else None,
            include_category=category,
            limit=limit
        )
        
        # 응답 구성
        policies = [p for p, score in results]
        scores = {p.plcy_no: score for p, score in results}
        
        serializer = PolicyListSerializer(policies, many=True)
        
        # 각 정책에 점수 추가
        data = serializer.data
        for item in data:
            item['match_score'] = scores.get(item['plcy_no'], 0)
        
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