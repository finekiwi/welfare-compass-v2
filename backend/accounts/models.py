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