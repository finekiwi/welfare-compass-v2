"""
알림 발송 서비스
신규 정책 → 매칭 회원 → 이메일 발송
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError

from accounts.models import Profile
from policies.models import Policy
from policies.services.matching import is_policy_matching_user
from .models import NotificationLog

logger = logging.getLogger(__name__)


def notify_matching_users(policy: Policy) -> dict:
    """
    신규 정책에 매칭되는 회원들에게 이메일 알림 발송
    
    Args:
        policy: 신규 Policy 객체
        
    Returns:
        dict: {'sent': int, 'skipped': int, 'failed': int}
    """
    stats = {'sent': 0, 'skipped': 0, 'failed': 0}
    
    # 알림 수신 동의한 회원들 조회
    eligible_profiles = Profile.objects.filter(
        email_notification_enabled=True,
        notification_email__isnull=False,
    ).exclude(notification_email='').select_related('user')
    
    logger.info(f"[알림] 정책 '{policy.title}' - 알림 대상 회원 {eligible_profiles.count()}명 조회")
    
    for profile in eligible_profiles:
        try:
            # 이미 발송한 적 있는지 확인
            if NotificationLog.objects.filter(user=profile.user, policy=policy).exists():
                stats['skipped'] += 1
                continue
            
            # 매칭 여부 확인 (matching.py 공통 함수 사용)
            user_info = profile.to_matching_dict()
            if not is_policy_matching_user(policy, user_info):
                stats['skipped'] += 1
                continue
            
            # 이메일 발송
            success = send_policy_notification(
                email=profile.notification_email,
                user_name=profile.user.username,
                policy=policy,
            )
            
            # 발송 이력 저장
            NotificationLog.objects.create(
                user=profile.user,
                policy=policy,
                email=profile.notification_email,
                status='sent' if success else 'failed',
                sent_at=timezone.now() if success else None,
            )
            
            if success:
                stats['sent'] += 1
            else:
                stats['failed'] += 1
                
        except IntegrityError:
            # 중복 발송 시도 (unique_together 위반)
            stats['skipped'] += 1
        except Exception as e:
            logger.error(f"[알림] 발송 실패 ({profile.user.username}): {e}")
            stats['failed'] += 1
    
    logger.info(f"[알림] 정책 '{policy.title}' 발송 완료: {stats}")
    return stats



def send_policy_notification(email: str, user_name: str, policy: Policy) -> bool:
    """
    이메일 발송
    
    Args:
        email: 수신자 이메일
        user_name: 수신자 이름
        policy: 정책 객체
        
    Returns:
        bool: 발송 성공 여부
    """
    subject = f"[복지나침반] 새로운 맞춤 정책 알림: {policy.title}"
    
    message = f"""
안녕하세요, {user_name}님!

회원님의 프로필과 매칭되는 새로운 정책이 등록되었습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 정책명: {policy.title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 정책 설명:
{policy.description[:300]}{'...' if len(policy.description) > 300 else ''}

📅 신청 기간: {policy.apply_start_date or '미정'} ~ {policy.apply_end_date or '미정'}

🔗 자세히 보기: {policy.apply_url or '복지나침반 앱에서 확인하세요'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

본 메일은 '정책정보 알림 수신 동의'에 따라 발송되었습니다.
알림 수신을 원하지 않으시면 마이페이지에서 설정을 변경해주세요.

복지나침반 드림
"""
    
    try:
        # 실제 이메일 발송
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"[이메일 발송 성공] {email} - {policy.title}")
        return True
        
    except Exception as e:
        logger.error(f"[이메일 발송 실패] {email}: {e}")
        return False
