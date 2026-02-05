"""
Django Signal: 신규 정책 감지 → 알림 발송 (비동기)
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from policies.models import Policy
from .tasks import schedule_policy_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Policy)
def notify_on_new_policy(sender, instance, created, **kwargs):
    """
    신규 정책 생성 시 매칭 회원에게 알림 발송 (비동기)
    
    Note: 
    - load_policies 커맨드의 update_or_create()에서도 호출됨
    - created=True일 때만 알림 발송 (업데이트 시 발송 안함)
    - 비동기 태스크로 실행되어 ETL 성능에 영향 없음
    """
    if not created:
        return
    
    logger.info(f"[시그널] 신규 정책 감지: {instance.title}")
    
    # 비동기 태스크로 알림 발송 (즉시 리턴)
    # Policy는 PK가 policy_id이므로 pk 사용
    schedule_policy_notification(instance.pk)
    logger.info(f"[시그널] 알림 태스크 큐에 등록됨: policy_id={instance.pk}")
