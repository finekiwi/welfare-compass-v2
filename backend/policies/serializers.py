from rest_framework import serializers
from .models import Policy, Category

class PosterUrlMixin:
    """포스터 URL을 절대경로로 반환하는 믹스인"""
    def get_poster_url(self, obj):
        if obj.poster:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.poster.url)
            return obj.poster.url
        return None

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


# =============================================================================
# [BRAIN4-23] API 응답 필드명은 프론트엔드 호환을 위해 옛 이름 유지
# - 백엔드 모델: 영문 (policy_id, title, description, ...)
# - API 응답: 옛 이름 (plcy_no, plcy_nm, plcy_expln_cn, ...)
# - source 파라미터로 매핑
# =============================================================================


class PolicyListSerializer(PosterUrlMixin, serializers.ModelSerializer):
    """목록용 - 간략한 정보 (프론트 호환: 옛 필드명 유지)"""
    plcy_no = serializers.CharField(source='policy_id')  # [RENAME] model: policy_id → API: plcy_no
    plcy_nm = serializers.CharField(source='title')  # [RENAME] model: title → API: plcy_nm
    aply_start_dt = serializers.DateField(source='apply_start_date')  # [ADD] 신청시작일
    aply_end_dt = serializers.DateField(source='apply_end_date')  # [RENAME] model: apply_end_date → API: aply_end_dt
    plcy_expln_cn = serializers.CharField(source='description')  # [RENAME] model: description → API: plcy_expln_cn
    plcy_sprt_cn = serializers.CharField(source='support_content')  # [RENAME] model: support_content → API: plcy_sprt_cn
    categories = CategorySerializer(many=True, read_only=True)
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = [
            'plcy_no',
            'plcy_nm',
            'district',
            'aply_start_dt',
            'aply_end_dt',
            'categories',
            'plcy_expln_cn',
            'plcy_sprt_cn',
            'poster_url',
        ]



class PolicyDetailSerializer(PosterUrlMixin, serializers.ModelSerializer):
    """상세용 - 전체 정보 (프론트 호환: 옛 필드명 유지)"""
    plcy_no = serializers.CharField(source='policy_id')
    plcy_nm = serializers.CharField(source='title')
    plcy_expln_cn = serializers.CharField(source='description')
    plcy_sprt_cn = serializers.CharField(source='support_content')
    sprt_trgt_min_age = serializers.IntegerField(source='age_min')
    sprt_trgt_max_age = serializers.IntegerField(source='age_max')
    earn_cnd_se_cd = serializers.CharField(source='income_level')
    earn_min_amt = serializers.IntegerField(source='income_min')
    earn_max_amt = serializers.IntegerField(source='income_max')
    mrg_stts_cd = serializers.CharField(source='marriage_status')
    job_cd = serializers.CharField(source='employment_status')
    school_cd = serializers.CharField(source='education_status')
    aply_start_dt = serializers.DateField(source='apply_start_date')
    aply_end_dt = serializers.DateField(source='apply_end_date')
    plcy_aply_mthd_cn = serializers.CharField(source='apply_method')
    aply_url_addr = serializers.CharField(source='apply_url')
    biz_prd_bgng_ymd = serializers.DateField(source='business_start_date')
    biz_prd_end_ymd = serializers.DateField(source='business_end_date')
    lclsf_nm = serializers.CharField(source='category')
    mclsf_nm = serializers.CharField(source='subcategory')
    frst_reg_dt = serializers.DateTimeField(source='created_at')
    last_mdfcn_dt = serializers.DateTimeField(source='updated_at')
    categories = CategorySerializer(many=True, read_only=True)
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = [
            'plcy_no',
            'plcy_nm',
            'plcy_expln_cn',
            'plcy_sprt_cn',
            'sprt_trgt_min_age',
            'sprt_trgt_max_age',
            'earn_cnd_se_cd',
            'earn_min_amt',
            'earn_max_amt',
            'mrg_stts_cd',
            'job_cd',
            'school_cd',
            'aply_start_dt',
            'aply_end_dt',
            'plcy_aply_mthd_cn',
            'aply_url_addr',
            'biz_prd_bgng_ymd',
            'biz_prd_end_ymd',
            'district',
            'lclsf_nm',
            'mclsf_nm',
            'categories',
            'frst_reg_dt',
            'last_mdfcn_dt',
            # Boolean fields
            'sbiz_cd',
            'is_for_single_parent',
            'is_for_disabled',
            'is_for_low_income',
            'is_for_newlywed',
            'poster_url',
        ]



# =============================================================================
# [BRAIN4-19] 달력용 Serializer
# =============================================================================
# 프론트엔드 calendar.api.ts에서 요구하는 형식:
# - plcy_no, plcy_nm (프론트 호환)
# - aplyYmd: "YYYYMMDD ~ YYYYMMDD"
# - bizPrdBgngYmd: "YYYYMMDD"
# - bizPrdEndYmd: "YYYYMMDD"
# =============================================================================

class CalendarEventSerializer(serializers.ModelSerializer):
    """달력 이벤트용 - 날짜 데이터 위주 (프론트 호환: 옛 필드명 유지)"""

    plcy_no = serializers.CharField(source='policy_id')  # [RENAME] model: policy_id → API: plcy_no
    plcy_nm = serializers.CharField(source='title')  # [RENAME] model: title → API: plcy_nm

    # 프론트 형식에 맞게 변환
    aplyYmd = serializers.SerializerMethodField()
    bizPrdBgngYmd = serializers.SerializerMethodField()
    bizPrdEndYmd = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = ['plcy_no', 'plcy_nm', 'aplyYmd', 'bizPrdBgngYmd', 'bizPrdEndYmd', 'category']

    def get_aplyYmd(self, obj):
        """신청기간: "YYYYMMDD ~ YYYYMMDD" 형식"""
        if obj.apply_start_date and obj.apply_end_date:
            start = obj.apply_start_date.strftime('%Y%m%d')
            end = obj.apply_end_date.strftime('%Y%m%d')
            return f"{start} ~ {end}"
        return None

    def get_bizPrdBgngYmd(self, obj):
        """사업시작일: "YYYYMMDD" 형식"""
        if obj.business_start_date:
            return obj.business_start_date.strftime('%Y%m%d')
        return None

    def get_bizPrdEndYmd(self, obj):
        """사업종료일: "YYYYMMDD" 형식"""
        if obj.business_end_date:
            return obj.business_end_date.strftime('%Y%m%d')
        return None

from .models import MapPOI

class MapPOISerializer(serializers.ModelSerializer):
    """지도 POI Serializer"""
    theme_name = serializers.CharField(source='theme.name', read_only=True)
    cot_conts_id = serializers.SerializerMethodField()
    cot_theme_id = serializers.SerializerMethodField()
    cot_theme_sub_id = serializers.SerializerMethodField()
    theme_icon_url = serializers.SerializerMethodField()

    class Meta:
        model = MapPOI
        fields = [
            'id', 
            'theme',
            'theme_name',
            'name', 
            'latitude', 
            'longitude', 
            'address', 
            'phone', 
            'detail_url',
            'cot_conts_id',
            'cot_theme_id',
            'cot_theme_sub_id',
            'theme_icon_url',
            'original_data'
        ]

    def get_cot_conts_id(self, obj):
        if isinstance(obj.original_data, dict):
            return obj.original_data.get('COT_CONTS_ID', '')
        return ''

    def get_cot_theme_id(self, obj):
        if isinstance(obj.original_data, dict):
            return obj.original_data.get('COT_THEME_ID', '')
        return ''

    def get_cot_theme_sub_id(self, obj):
        if isinstance(obj.original_data, dict):
            return obj.original_data.get('COT_THEME_SUB_ID', '')
        return ''

    def get_theme_icon_url(self, obj):
        try:
            sub_id = None
            if isinstance(obj.original_data, dict):
                sub_id = obj.original_data.get('COT_THEME_SUB_ID')
            
            if sub_id and hasattr(obj, 'theme') and obj.theme and hasattr(obj.theme, 'metadata'):
                metadata = obj.theme.metadata
                if isinstance(metadata, dict):
                    subcates = metadata.get('SUBCATE', [])
                    if isinstance(subcates, list):
                        for c in subcates:
                            if isinstance(c, dict) and str(c.get('SUB_CATE_ID', '')) == str(sub_id):
                                uri = c.get('SUB_CATE_IMG_URI')
                                if uri:
                                    if str(uri).startswith('/'):
                                        return f"https://map.seoul.go.kr{uri}"
                                    return str(uri)
            return ''
        except Exception:
            return ''
