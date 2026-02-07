from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from policies.models import Category
from policies.services.matching_keys import (
    JOB_STATUS_TO_CODE,
    JOB_STATUS_TO_KOREAN,
    EDUCATION_STATUS_TO_CODE,
    MARRIAGE_STATUS_TO_CODE,
    HOUSING_TYPE_TO_KOREAN,
)


class Profile(models.Model):
    """사용자 프로필 - 정책 매칭에 필요한 정보"""
    
    # ==========================================================================
    # [BRAIN4-31] 취업상태 선택지
    # - API jobCd 코드와 매핑: 0013001(재직자), 0013002(자영업자), 0013003(미취업자),
    #   0013004(프리랜서), 0013006(예비창업자)
    # - 'student'는 API에 없지만 사용자 UX상 필요 → 매칭 시 미취업자(0013003)로 처리
    # - 'other' 삭제: 매칭에서 사용 안 함, 애매한 선택지 제거
    # - 'self_employed' 추가: 자영업자(0013002)는 프리랜서(0013004)와 구분 필요
    # ==========================================================================
    JOB_STATUS_CHOICES = [
        ('employed', '재직중'),        # API: 0013001 (재직자)
        ('self_employed', '자영업자'), # API: 0013002 (자영업자) - 신규 추가
        ('unemployed', '미취업'),      # API: 0013003 (미취업자)
        ('job_seeking', '구직중'),     # API: 0013003 (미취업자와 동일 매핑)
        ('student', '학생'),           # API 없음 → 매칭 시 0013003으로 처리
        ('startup', '창업준비'),       # API: 0013006 (예비창업자)
        ('freelancer', '프리랜서'),    # API: 0013004 (프리랜서)
    ]
    
    # ==========================================================================
    # [BRAIN4-31] 학력상태 선택지
    # - API schoolCd 코드 기반 전면 재구성
    # - 기존 문제: '재학/졸업'이 고졸인지 대졸인지 모호함
    # - 변경: 고졸 미만 ~ 석박사까지 명확하게 구분
    # - 'university_leave'(대학휴학)은 API에 없지만 UX상 필요 → 매칭 시 대학재학으로 처리
    # - 'other' 삭제: 매칭에서 사용 안 함
    # ==========================================================================
    EDUCATION_STATUS_CHOICES = [
        ('below_high_school', '고졸 미만'),       # API: 0049001
        ('high_school_enrolled', '고교 재학'),   # API: 0049002 (+ 0049003 고졸예정 포함 매칭)
        ('high_school', '고졸'),                 # API: 0049004
        ('university_enrolled', '대학 재학'),    # API: 0049005
        ('university_leave', '대학 휴학'),       # API 없음 → 매칭 시 0049005로 처리
        ('university', '대졸'),                  # API: 0049007 (+ 0049006 대졸예정 포함)
        ('graduate_school', '석박사'),           # API: 0049008
    ]
    
    # ==========================================================================
    # [BRAIN4-31] 혼인상태 선택지
    # - API mrgSttsCd 코드: 0055001(기혼), 0055002(미혼), 0055003(제한없음)
    # - 'other' 삭제: 법적으로 미혼/기혼만 존재, 동거는 미혼으로 처리
    # ==========================================================================
    MARRIAGE_STATUS_CHOICES = [
        ('single', '미혼'),   # API: 0055002
        ('married', '기혼'),  # API: 0055001
    ]
    
    INCOME_LEVEL_CHOICES = [
        ('below_50', '기준중위소득 50% 이하'),
        ('below_100', '기준중위소득 100% 이하'),
        ('above_100', '기준중위소득 100% 초과'),
        ('unknown', '모름'),
    ]
    
    # ==========================================================================
    # [BRAIN4-31] 주거형태 선택지
    # - 2026-02-03 회의 결정: 7개 → 3개로 단순화
    # - 고시원, 공공임대 → '월세'로 통합 (임차 형태)
    # - 부모님집 → '자가'로 통합 (주거비 부담 없음)
    # - 'other' 삭제: 매칭에서 사용 안 함
    # - 기존 데이터 마이그레이션 필요: gosiwon/public→monthly, parents→owned
    # ==========================================================================
    HOUSING_TYPE_CHOICES = [
        ('jeonse', '전세'),
        ('monthly', '월세'),  # 고시원, 공공임대 포함
        ('owned', '자가'),    # 부모님집 포함
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # 기본 정보
    birth_year = models.IntegerField(null=True, blank=True, verbose_name='출생년도')
    district = models.CharField(max_length=20, blank=True, verbose_name='거주 구')
    
    # 소득/취업
    income_level = models.CharField(
        max_length=20,
        choices=INCOME_LEVEL_CHOICES,
        blank=True,
        verbose_name='소득수준'
    )
    income_amount = models.IntegerField(
        null=True, blank=True,
        verbose_name='월 소득(만원)',
        help_text='월 평균 소득 (만원 단위)'
    )
    job_status = models.CharField(
        max_length=20, 
        choices=JOB_STATUS_CHOICES, 
        blank=True,
        verbose_name='취업상태'
    )
    
    # 학력
    education_status = models.CharField(
        max_length=20, 
        choices=EDUCATION_STATUS_CHOICES, 
        blank=True,
        verbose_name='학력상태'
    )
    
    # 결혼
    marriage_status = models.CharField(
        max_length=20, 
        choices=MARRIAGE_STATUS_CHOICES, 
        blank=True,
        verbose_name='혼인상태'
    )
    
    # 관심 분야
    interests = models.ManyToManyField(Category, blank=True, related_name='interested_profiles')
    
    # ===== 추가 필드들 (matching.py 호환) =====
    
    # 주거 정보
    housing_type = models.CharField(
        max_length=20,
        choices=HOUSING_TYPE_CHOICES,
        blank=True,
        verbose_name='주거형태'
    )
    
    # 가구 정보
    household_size = models.IntegerField(
        null=True, blank=True,
        verbose_name='가구원 수',
        help_text='본인 포함 가구원 수'
    )
    
    # 자녀 정보
    has_children = models.BooleanField(
        default=False,
        verbose_name='자녀 유무'
    )
    children_ages = models.JSONField(
        default=list, blank=True,
        verbose_name='자녀 나이',
        help_text='자녀 나이 리스트 (예: [5, 8])'
    )
    
    # 특수 조건 (신혼, 한부모, 장애 등)
    special_conditions = models.JSONField(
        default=list, blank=True,
        verbose_name='특수조건',
        help_text='해당하는 특수조건 리스트 (예: ["신혼", "장애"])'
    )
    
    # 필요 분야
    needs = models.JSONField(
        default=list, blank=True,
        verbose_name='필요분야',
        help_text='필요한 지원 분야 리스트 (예: ["주거", "일자리"])'
    )
    
    # 이메일 알림 설정
    email_notification_enabled = models.BooleanField(
        default=False,
        verbose_name='정책정보 알림 수신 동의'
    )
    notification_email = models.EmailField(
        blank=True, null=True,
        verbose_name='알림 수신 이메일',
        help_text='정책 알림을 받을 이메일 주소'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profile'
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    @property
    def age(self):
        """현재 나이 계산"""
        if self.birth_year:
            from datetime import date
            return date.today().year - self.birth_year
        return None
    
    def to_matching_dict(self):
        """
        matching.py 호환 딕셔너리 변환

        [BRAIN4-31] 변경사항:
        - job_code, education_code, marriage_code 추가: Policy API 코드와 비교용
        - education_status, marriage_status 추가: 기존 누락 필드
        - housing_type: 한글 값 (점수 계산용)
        """
        return {
            # 기본 정보
            'age': self.age,
            'residence': self.district,

            # 취업 상태
            'employment_status': self._convert_job_status(),  # 한글 (점수 계산용) - 기존 호환
            'job_code': self._get_job_code(),                 # API 코드 (필터링용) - 신규

            # 학력 상태 (API 코드) - [BRAIN4-31] 신규 추가
            'education_code': self._get_education_code(),

            # 결혼 상태 (API 코드) - [BRAIN4-31] 신규 추가
            'marriage_code': self._get_marriage_code(),

            # 주거 형태 (한글 - 점수 계산용)
            'housing_type': self._convert_housing_type(),

            # 소득/가구 정보
            'income': self.income_amount,
            'household_size': self.household_size,

            # 자녀 정보
            'has_children': self.has_children,
            'children_ages': self.children_ages or [],

            # 특수조건 및 필요분야
            'special_conditions': self.special_conditions or [],
            'needs': self.needs or [],

            # 관심분야 (카테고리명 리스트)
            'interests': list(self.interests.values_list('name', flat=True)),
        }
    
    # ==========================================================================
    # [BRAIN4-31] Profile 값 → 한글/API 코드 변환 함수들
    # - 한글 변환: matching.py 점수 계산용 (기존 호환)
    # - API 코드 변환: Policy 필터링용 (신규)
    # ==========================================================================

    def _convert_job_status(self):
        """job_status를 한글 값으로 변환 (matching.py 점수 계산용)"""
        return JOB_STATUS_TO_KOREAN.get(self.job_status, '')

    def _get_job_code(self):
        """job_status를 API jobCd 코드로 변환"""
        return JOB_STATUS_TO_CODE.get(self.job_status, '')

    def _get_education_code(self):
        """education_status를 API schoolCd 코드로 변환"""
        return EDUCATION_STATUS_TO_CODE.get(self.education_status, '')

    def _get_marriage_code(self):
        """marriage_status를 API mrgSttsCd 코드로 변환"""
        return MARRIAGE_STATUS_TO_CODE.get(self.marriage_status, '')
    
    def _convert_housing_type(self):
        """housing_type을 한글 값으로 변환 (matching.py 점수 계산용)"""
        return HOUSING_TYPE_TO_KOREAN.get(self.housing_type, '')


# User 생성 시 자동으로 Profile 생성
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class Scrap(models.Model):
    """사용자의 관심 정책 스크랩"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scraps')
    policy = models.ForeignKey('policies.Policy', on_delete=models.CASCADE, related_name='scraps')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'scrap'
        unique_together = ['user', 'policy']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.policy.title}"  # [RENAME] plcy_nm → title
