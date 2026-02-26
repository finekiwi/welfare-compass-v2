from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        db_table = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Policy(models.Model):
    # 기본 정보
    policy_id = models.CharField(max_length=30, primary_key=True)  # [RENAME] plcy_no → policy_id
    title = models.CharField(max_length=200)  # [RENAME] plcy_nm → title
    description = models.TextField(blank=True)  # [RENAME] plcy_expln_cn → description
    support_content = models.TextField(blank=True)  # [RENAME] plcy_sprt_cn → support_content

    # 자격 요건
    age_min = models.IntegerField(null=True, blank=True)  # [RENAME] sprt_trgt_min_age → age_min
    age_max = models.IntegerField(null=True, blank=True)  # [RENAME] sprt_trgt_max_age → age_max
    # [REMOVED] sprt_trgt_age_lmt_yn 삭제
    income_level = models.CharField(max_length=20, blank=True)  # [RENAME] earn_cnd_se_cd → income_level
    income_min = models.IntegerField(null=True, blank=True)  # [RENAME] earn_min_amt → income_min
    income_max = models.IntegerField(null=True, blank=True)  # [RENAME] earn_max_amt → income_max
    marriage_status = models.CharField(max_length=20, blank=True)  # [RENAME] mrg_stts_cd → marriage_status
    employment_status = models.CharField(max_length=100, blank=True)  # [RENAME] job_cd → employment_status
    education_status = models.CharField(max_length=100, blank=True)  # [RENAME] school_cd → education_status

    # 특수조건 필드 - API 코드 기반 필터링 (변경 없음)
    sbiz_cd = models.CharField(
        max_length=200,
        blank=True,
        help_text='API 원본 sbizCd (콤마 구분)'
    )

    is_for_single_parent = models.BooleanField(
        default=False,
        help_text='한부모 전용 정책 (sbizCd: 0014004)'
    )
    is_for_disabled = models.BooleanField(
        default=False,
        help_text='장애인 전용 정책 (sbizCd: 0014005)'
    )
    is_for_low_income = models.BooleanField(
        default=False,
        help_text='기초수급자 전용 정책 (sbizCd: 0014003)'
    )
    is_for_newlywed = models.BooleanField(
        default=False,
        help_text='신혼부부 전용 정책 (API 코드 없음 → 텍스트 파싱)'
    )

    # 신청 정보
    apply_start_date = models.DateField(null=True, blank=True)  # [RENAME] aply_start_dt → apply_start_date
    apply_end_date = models.DateField(null=True, blank=True)  # [RENAME] aply_end_dt → apply_end_date
    apply_method = models.TextField(blank=True)  # [RENAME] plcy_aply_mthd_cn → apply_method
    apply_url = models.CharField(max_length=500, blank=True)  # [RENAME] aply_url_addr → apply_url

    # 사업기간
    business_start_date = models.DateField(  # [RENAME] biz_prd_bgng_ymd → business_start_date
        null=True, blank=True,
        help_text='사업시작일 - 원본: bizPrdBgngYmd'
    )
    business_end_date = models.DateField(  # [RENAME] biz_prd_end_ymd → business_end_date
        null=True, blank=True,
        help_text='사업종료일 - 원본: bizPrdEndYmd'
    )

    # 지역 (변경 없음)
    district = models.CharField(max_length=20, null=True, blank=True)

    # 카테고리 (대분류/중분류)
    category = models.CharField(  # [RENAME] lclsf_nm → category
        max_length=50, blank=True,
        help_text='대분류 (일자리, 주거, 교육, 복지문화, 참여권리)'
    )
    subcategory = models.CharField(  # [RENAME] mclsf_nm → subcategory
        max_length=50, blank=True,
        help_text='중분류 (원본 API mclsfNm)'
    )

    # 카테고리 (M:N, 변경 없음)
    categories = models.ManyToManyField(Category, related_name='policies')

    # 메타
    created_at = models.DateTimeField(null=True, blank=True)  # [RENAME] frst_reg_dt → created_at
    updated_at = models.DateTimeField(null=True, blank=True)  # [RENAME] last_mdfcn_dt → updated_at

    class Meta:
        db_table = 'policy'

    def __str__(self):
        return self.title  # [RENAME] self.plcy_nm → self.title


class MapTheme(models.Model):
    theme_id = models.CharField(max_length=50, unique=True, help_text="스마트 서울맵 테마 ID")
    name = models.CharField(max_length=100, help_text="테마 이름 (예: [동행]청년공간)")
    
    # Original data backup (JSON) for theme metadata including SUBCATE icons
    metadata = models.JSONField(default=dict, blank=True, help_text="API 원본 테마 데이터")

    def __str__(self):
        return self.name


class MapPOI(models.Model):
    theme = models.ForeignKey(MapTheme, on_delete=models.CASCADE, related_name="pois")
    name = models.CharField(max_length=200, help_text="장소명")
    latitude = models.FloatField(help_text="위도 (WGS84)")
    longitude = models.FloatField(help_text="경도 (WGS84)")
    address = models.CharField(max_length=500, blank=True, help_text="주소")
    phone = models.CharField(max_length=50, blank=True, help_text="연락처")
    detail_url = models.URLField(blank=True, help_text="상세 정보 URL")
    
    # Original data backup (JSON)
    original_data = models.JSONField(default=dict, blank=True, help_text="API 원본 데이터")

    def __str__(self):
        return self.name
