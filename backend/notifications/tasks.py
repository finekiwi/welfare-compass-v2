"""
비동기 태스크 정의 (django-q2)

이메일 발송 등 시간이 오래 걸리는 작업을 백그라운드에서 처리
"""
import logging
from django_q.tasks import async_task

logger = logging.getLogger(__name__)


def notify_matching_users_task(policy_id: str) -> dict:
    """
    신규 정책에 매칭되는 회원들에게 이메일 알림 발송 (비동기 태스크)
    
    Args:
        policy_id: Policy의 ID (policy_id)
        
    Returns:
        dict: {'sent': int, 'skipped': int, 'failed': int}
    """
    from policies.models import Policy
    from .services import notify_matching_users
    
    try:
        policy = Policy.objects.get(policy_id=policy_id)
        logger.info(f"[비동기 태스크] 정책 알림 시작: {policy.title}")
        
        stats = notify_matching_users(policy)
        
        logger.info(f"[비동기 태스크] 정책 알림 완료: {stats}")
        return stats
        
    except Policy.DoesNotExist:
        logger.error(f"[비동기 태스크] 정책을 찾을 수 없음: policy_id={policy_id}")
        return {'sent': 0, 'skipped': 0, 'failed': 0, 'error': 'Policy not found'}
    except Exception as e:
        logger.error(f"[비동기 태스크] 알림 발송 중 오류: {e}")
        return {'sent': 0, 'skipped': 0, 'failed': 0, 'error': str(e)}


def schedule_policy_notification(policy_id: str):
    """
    정책 알림 태스크를 큐에 등록 (즉시 리턴)
    
    Args:
        policy_id: Policy의 ID (policy_id)
    """
    async_task(
        'notifications.tasks.notify_matching_users_task',
        policy_id,
        task_name=f'policy_notification_{policy_id}',
        hook='notifications.tasks.notification_complete_hook',
    )
    logger.info(f"[태스크 등록] policy_id={policy_id} 알림 태스크 큐에 추가됨")


def notification_complete_hook(task):
    """
    태스크 완료 후 콜백 (성공/실패 로깅)
    """
    if task.success:
        logger.info(f"[태스크 완료] {task.name}: {task.result}")
    else:
        logger.error(f"[태스크 실패] {task.name}: {task.result}")
