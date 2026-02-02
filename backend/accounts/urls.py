from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import SignupView, ProfileView, ScrapListView, ScrapDetailView, DeleteAccountView, CheckUsernameView


urlpatterns = [
    # 인증
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-username/', CheckUsernameView.as_view(), name='check-username'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 프로필
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # 스크랩
    path('scraps/', ScrapListView.as_view(), name='scrap-list'),
    path('scraps/<str:policy_id>/', ScrapDetailView.as_view(), name='scrap-detail'),  # [RENAME] plcy_no → policy_id
    
    # 회원탈퇴
    path('delete/', DeleteAccountView.as_view(), name='delete-account'),
]