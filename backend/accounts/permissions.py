from rest_framework import permissions
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.cache import cache

REAUTH_TOKEN_BLACKLIST_PREFIX = "reauth_blacklist:"
REAUTH_TOKEN_MAX_AGE = 300  # 5분


def blacklist_reauth_token(token: str) -> None:
    """사용된 reauth 토큰을 만료 시간까지 블랙리스트에 등록"""
    cache.set(f"{REAUTH_TOKEN_BLACKLIST_PREFIX}{token}", True, timeout=REAUTH_TOKEN_MAX_AGE)


class IsReauthenticated(permissions.BasePermission):
    """
    민감한 작업 전 재인증 여부를 확인하는 권한
    헤더의 X-Reauth-Token 이 5분 이내에 발급된 유효한 토큰인지 검사.
    소셜 로그인 사용자를 포함한 모든 사용자가 유효한 토큰을 제출해야 통과됨.
    한 번 사용된 토큰은 블랙리스트 처리되어 재사용 불가.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        token = request.headers.get('X-Reauth-Token')
        if not token:
            return False

        # 블랙리스트 확인 (이미 사용된 토큰)
        if cache.get(f"{REAUTH_TOKEN_BLACKLIST_PREFIX}{token}"):
            return False

        signer = TimestampSigner()
        try:
            user_id = signer.unsign(token, max_age=REAUTH_TOKEN_MAX_AGE)
            if str(request.user.id) == str(user_id):
                return True
        except (BadSignature, SignatureExpired):
            return False

        return False
