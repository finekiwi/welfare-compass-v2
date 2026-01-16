from rest_framework import serializers
from .models import Policy, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class PolicyListSerializer(serializers.ModelSerializer):
    """목록용 - 간략한 정보"""
    categories = CategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Policy
        fields = [
            'plcy_no',
            'plcy_nm',
            'district',
            'aply_end_dt',
            'categories',
        ]


class PolicyDetailSerializer(serializers.ModelSerializer):
    """상세용 - 전체 정보"""
    categories = CategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Policy
        fields = '__all__'


# =============================================================================
# [BRAIN4-19] 달력용 Serializer
# =============================================================================
# 프론트엔드 calendar.api.ts에서 요구하는 형식:
# - aplyYmd: "YYYYMMDD ~ YYYYMMDD"
# - bizPrdBgngYmd: "YYYYMMDD"
# - bizPrdEndYmd: "YYYYMMDD"
# =============================================================================

class CalendarEventSerializer(serializers.ModelSerializer):
    """달력 이벤트용 - 날짜 데이터 위주"""
    
    # 프론트 형식에 맞게 변환
    aplyYmd = serializers.SerializerMethodField()
    bizPrdBgngYmd = serializers.SerializerMethodField()
    bizPrdEndYmd = serializers.SerializerMethodField()
    
    class Meta:
        model = Policy
        fields = ['plcy_no', 'plcy_nm', 'aplyYmd', 'bizPrdBgngYmd', 'bizPrdEndYmd']
    
    def get_aplyYmd(self, obj):
        """신청기간: "YYYYMMDD ~ YYYYMMDD" 형식"""
        if obj.aply_start_dt and obj.aply_end_dt:
            start = obj.aply_start_dt.strftime('%Y%m%d')
            end = obj.aply_end_dt.strftime('%Y%m%d')
            return f"{start} ~ {end}"
        return None
    
    def get_bizPrdBgngYmd(self, obj):
        """사업시작일: "YYYYMMDD" 형식"""
        if obj.biz_prd_bgng_ymd:
            return obj.biz_prd_bgng_ymd.strftime('%Y%m%d')
        return None
    
    def get_bizPrdEndYmd(self, obj):
        """사업종료일: "YYYYMMDD" 형식"""
        if obj.biz_prd_end_ymd:
            return obj.biz_prd_end_ymd.strftime('%Y%m%d')
        return None