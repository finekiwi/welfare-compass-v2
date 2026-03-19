"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.views.static import serve
from django.db import connection
from accounts.views import GoogleLogin, FindUsernameView, PasswordResetConfirmRedirectView, AxesLockedLoginView, CustomPasswordResetView, clean_logout, DisabledPasswordChangeView



def health_check(request):
    """Docker healthcheck 용 엔드포인트. DB round-trip 확인 포함."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "detail": str(e)}, status=503)


urlpatterns = [
    path('api/health/', health_check),
    path('admin/', admin.site.urls),
    path('api/policies/', include('policies.urls')),
    path('api/accounts/', include('accounts.urls')), # 기존 커스텀 (유지)
    
    # dj-rest-auth & allauth
    path('api/auth/login/', AxesLockedLoginView.as_view(), name='rest_login'),  # 계정 잠금 체크 포함
    path('api/auth/logout/', clean_logout, name='rest_logout'),   # [보안] 쿠키 완전 삭제 (순수 Django 함수형 뷰)
    path('api/auth/password/change/', DisabledPasswordChangeView.as_view(), name='rest_password_change_disabled'),
    path('api/auth/password/reset/', CustomPasswordResetView.as_view(), name='rest_password_reset'), # [커스텀] 이메일 존재 여부 확인
    path('api/auth/', include('dj_rest_auth.urls')),  # 위에서 login/logout/password/reset 오버라이드 후 나머지
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/google/login/', GoogleLogin.as_view(), name='google_login'),
    path('api/auth/find/username/', FindUsernameView.as_view(), name='find_username'), # [이동] 일관성을 위해 auth 경로로 이동
    
    # 비밀번호 재설정 이메일 링크 리다이렉트 (Backend -> Frontend)
    path('password-reset/confirm/<uidb64>/<token>/', PasswordResetConfirmRedirectView.as_view(), name='password_reset_confirm'),
    
    # [FIX] Google Login 시 allauth가 내부적으로 'account_signup'을 찾음 (사용하지 않더라도 선언 필요)
    path('api/auth/dummy-signup/', lambda request: HttpResponseRedirect(settings.FRONTEND_URL + '/signup'), name='account_signup'),
    path('api/auth/dummy-password/reset/', lambda request: HttpResponseRedirect(settings.FRONTEND_URL + '/login'), name='account_reset_password'),
    path('api/auth/dummy-email/', lambda request: HttpResponseRedirect(settings.FRONTEND_URL + '/profile'), name='account_email'),
    # path('api/auth/google/', include('allauth.socialaccount.providers.google.urls')), # (필요 시 유지, REST에서는 위 View 사용)

    path('api/v1/chat/', include('chat.urls')),  # [BRAIN4-20] Chat API
]

# Docker/Gunicorn 환경에서도 admin static/media를 Django에서 직접 서빙한다.
# NOTE: django.conf.urls.static.static()은 DEBUG=False일 때 빈 리스트를 반환하므로
# re_path + serve를 사용해 명시적으로 라우팅한다.
urlpatterns += [
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
