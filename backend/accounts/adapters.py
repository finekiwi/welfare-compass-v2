from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        # 1. Frontend URL 설정 (환경 변수 또는 하드코딩)
        # 개발 환경: localhost:3000
        # 배포 환경: 실제 도메인
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        
        # 2. 이메일 인증 키
        key = emailconfirmation.key
        
        # 3. 프론트엔드 라우트 주소 반환
        return f"{frontend_url}/auth/confirm-email/{key}/"
        
    def get_password_reset_url(self, request, user, temp_key, **kwargs):
        # 1. Frontend URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        
        # 2. UIDD64 처리 (allauth 내부 로직과 맞춤)
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # 3. 프론트엔드 비밀번호 재설정 페이지로 이동
        # URL 형태: /auth/password-reset/confirm/[uid]/[token]
        return f"{frontend_url}/auth/password-reset/confirm/{uid}/{temp_key}/"
