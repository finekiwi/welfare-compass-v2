from rest_framework import permissions
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

class IsReauthenticated(permissions.BasePermission):
    """
    민감한 작업 전 재인증 여부를 확인하는 권한
    헤더의 X-Reauth-Token 이 5분 이내에 발급된 유효한 토큰인지 검사.
    소셜 로그인 사용자를 포함한 모든 사용자가 유효한 토큰을 제출해야 통과됨.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # X-Reauth-Token 검증 (모든 사용자 공통 적용)
        token = request.headers.get('X-Reauth-Token')
        if not token:
            return False
            
        signer = TimestampSigner()
        try:
            # max_age: 초 단위 (5분 = 300초)
            user_id = signer.unsign(token, max_age=300)
            if str(request.user.id) == str(user_id):
                return True
        except (BadSignature, SignatureExpired):
            return False
            
        return False
