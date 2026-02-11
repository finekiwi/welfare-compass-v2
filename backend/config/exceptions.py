"""
커스텀 DRF 예외 처리기

django-axes의 AxesBackendPermissionDenied 예외를 DRF 응답으로 변환합니다.
axes는 Django의 authenticate() 레벨에서 동작하지만,
DRF는 별도의 예외 처리 체인을 사용하므로,
잠금 예외를 직접 잡아서 403 응답으로 변환해야 합니다.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from axes.exceptions import AxesBackendPermissionDenied


def custom_exception_handler(exc, context):
    """DRF 예외 처리기 + django-axes 잠금 처리"""

    # axes 잠금 예외만 처리 (일반 PermissionDenied는 DRF 기본 처리기에 위임)
    if isinstance(exc, AxesBackendPermissionDenied):
        return Response(
            {"error": "로그인 시도가 너무 많습니다. 5분 후 다시 시도해주세요."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # 기본 DRF 예외 처리
    response = exception_handler(exc, context)
    return response
