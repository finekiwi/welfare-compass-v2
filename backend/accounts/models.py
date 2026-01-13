from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from policies.models import Category


class Profile(models.Model):
    """사용자 프로필 - 정책 매칭에 필요한 정보"""
    
    JOB_STATUS_CHOICES = [
        ('employed', '재직중'),
        ('unemployed', '미취업'),
        ('job_seeking', '구직중'),
        ('student', '학생'),
        ('startup', '창업준비'),
        ('freelancer', '프리랜서'),
        ('other', '기타'),
    ]
    
    EDUCATION_STATUS_CHOICES = [
        ('enrolled', '재학'),
        ('on_leave', '휴학'),
        ('graduated', '졸업'),
        ('dropout', '중퇴'),
        ('other', '기타'),
    ]
    
    MARRIAGE_STATUS_CHOICES = [
        ('single', '미혼'),
        ('married', '기혼'),
        ('other', '기타'),
    ]
    
    INCOME_LEVEL_CHOICES = [
        ('below_50', '기준중위소득 50% 이하'),
        ('below_100', '기준중위소득 100% 이하'),
        ('above_100', '기준중위소득 100% 초과'),
        ('unknown', '모름'),
    ]
    
    # 주거형태 선택지
    HOUSING_TYPE_CHOICES = [
        ('jeonse', '전세'),
        ('monthly', '월세'),
        ('owned', '자가'),
        ('gosiwon', '고시원'),
        ('parents', '부모님집'),
        ('public', '공공임대'),
        ('other', '기타'),
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
        """matching.py 호환 딕셔너리 변환"""
        return {
            'age': self.age,
            'residence': self.district,
            'employment_status': self._convert_job_status(),
            'housing_type': self._convert_housing_type(),
            'income': self.income_amount,
            'household_size': self.household_size,
            'has_children': self.has_children,
            'children_ages': self.children_ages or [],
            'special_conditions': self.special_conditions or [],
            'needs': self.needs or [],
        }
    
    def _convert_job_status(self):
        """job_status를 matching.py 형식으로 변환"""
        mapping = {
            'employed': '재직',
            'job_seeking': '구직중',
            'unemployed': '무직',
            'student': '학생',
        }
        return mapping.get(self.job_status, '')
    
    def _convert_housing_type(self):
        """housing_type을 matching.py 형식으로 변환"""
        mapping = {
            'jeonse': '전세',
            'monthly': '월세',
            'gosiwon': '고시원',
            'public': '임대',
        }
        return mapping.get(self.housing_type, '')


# User 생성 시 자동으로 Profile 생성
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

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
        return f"{self.user.username} - {self.policy.plcy_nm}"