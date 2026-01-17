import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ChatSession(models.Model):
    """
    채팅 세션
    
    - 사용자가 채팅 시작하면 세션 1개 생성
    - 세션 안에 메시지들이 쌓임 (멀티턴 지원)
    - 30분 지나면 만료 (기능명세서: TTL 30분)
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text='UUID로 생성 (보안: 추측 불가)'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_sessions',
        help_text='비로그인 사용자는 null'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text='세션 만료 시간 (기본 30분)')

    class Meta:
        db_table = 'chat_session'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """세션 생성 시 expires_at 자동 설정 (30분 후)"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)

    def is_expired(self):
        """만료 여부 체크"""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Session {self.id} ({self.user or 'anonymous'})"


class ChatMessage(models.Model):
    """
    채팅 메시지
    
    - 세션에 속한 개별 메시지
    - role: user(사용자) 또는 assistant(AI)
    - metadata: LLM 연동 시 추출된 정보, 검색 결과 등 저장
    """
    ROLE_CHOICES = [
        ('user', '사용자'),
        ('assistant', '어시스턴트'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES,
        help_text='user 또는 assistant'
    )
    content = models.TextField(help_text='메시지 내용')
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='추출된 정보, 검색 결과, 에이전트 로그 등 (LLM 연동용)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_message'
        ordering = ['created_at']  # 시간순 정렬 (멀티턴 대화 흐름 유지)

    def __str__(self):
        return f"[{self.role}] {self.content[:30]}..."
