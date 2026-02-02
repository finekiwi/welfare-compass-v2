"""
알림 발송 이력 모델
중복 발송 방지 및 발송 이력 추적용
"""
from django.db import models
from django.contrib.auth.models import User
from policies.models import Policy


class NotificationLog(models.Model):
    """알림 발송 이력"""
    
    STATUS_CHOICES = [
        ('pending', '발송대기'),
        ('sent', '발송완료'),
        ('failed', '발송실패'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_logs')
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='notification_logs')
    
    email = models.EmailField(verbose_name='발송 이메일')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    error_message = models.TextField(blank=True, verbose_name='오류 메시지')
    
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notification_log'
        unique_together = ['user', 'policy']  # 같은 정책 중복 발송 방지
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.policy.title} ({self.status})"
