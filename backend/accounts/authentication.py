from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # 1. 헤더에서 토큰 확인 (기본 동작)
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        # 2. 쿠키에서 토큰 확인
        simple_jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
        auth_cookie_name = simple_jwt_settings.get('AUTH_COOKIE', 'access_token')
        raw_token = request.COOKIES.get(auth_cookie_name)
        if raw_token is not None:
            try:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
            except Exception:
                # 쿠키 토큰이 유효하지 않으면 무시 (로그인 안 된 상태로 처리)
                return None
        
        return None
