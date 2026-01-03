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
    plcy_no = models.CharField(max_length=30, primary_key=True)
    plcy_nm = models.CharField(max_length=200)
    plcy_expln_cn = models.TextField(blank=True)
    plcy_sprt_cn = models.TextField(blank=True)

    # 자격 요건
    sprt_trgt_min_age = models.IntegerField(null=True, blank=True)
    sprt_trgt_max_age = models.IntegerField(null=True, blank=True)
    sprt_trgt_age_lmt_yn = models.CharField(max_length=1, blank=True)
    earn_cnd_se_cd = models.CharField(max_length=20, blank=True)
    earn_min_amt = models.IntegerField(null=True, blank=True)
    earn_max_amt = models.IntegerField(null=True, blank=True)
    mrg_stts_cd = models.CharField(max_length=20, blank=True)
    job_cd = models.CharField(max_length=100, blank=True)
    school_cd = models.CharField(max_length=100, blank=True)

    # 신청 정보
    aply_start_dt = models.DateField(null=True, blank=True)
    aply_end_dt = models.DateField(null=True, blank=True)
    plcy_aply_mthd_cn = models.TextField(blank=True)
    aply_url_addr = models.CharField(max_length=500, blank=True)

    # 지역
    district = models.CharField(max_length=20, null=True, blank=True)

    # 카테고리 (M:N)
    categories = models.ManyToManyField(Category, related_name='policies')

    # 메타
    frst_reg_dt = models.DateTimeField(null=True, blank=True)
    last_mdfcn_dt = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'policy'

    def __str__(self):
        return self.plcy_nm