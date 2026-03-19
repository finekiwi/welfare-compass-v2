from django.urls import path
from .views import (
    ProfileView, ScrapListView, ScrapDetailView, 
    DeleteAccountView, CheckUsernameView, VerifyPasswordView, VerifySocialView,
    ChangePasswordView
    # FindUsernameView,  <-- config/urls.py로 이동
    # SignupView, CustomLoginView, CustomRefreshView, LogoutView
)


urlpatterns = [
    # 인증 (dj-rest-auth로 대체됨 - /api/auth/...)
    # path('signup/', SignupView.as_view(), name='signup'),
    path('check-username/', CheckUsernameView.as_view(), name='check-username'),
    path('verify-password/', VerifyPasswordView.as_view(), name='verify-password'),
    path('verify-social/', VerifySocialView.as_view(), name='verify-social'),
    path('password/change/', ChangePasswordView.as_view(), name='password-change'),
    
    # 프로필
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # 스크랩
    path('scraps/', ScrapListView.as_view(), name='scrap-list'),
    path('scraps/<str:policy_id>/', ScrapDetailView.as_view(), name='scrap-detail'),  # [RENAME] plcy_no → policy_id
    
    # 회원탈퇴
    path('delete/', DeleteAccountView.as_view(), name='delete-account'),
]
