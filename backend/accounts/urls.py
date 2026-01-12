from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import SignupView, ProfileView, ScrapListView, ScrapDetailView


urlpatterns = [
    # 인증
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 프로필
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # 스크랩
    path('scraps/', ScrapListView.as_view(), name='scrap-list'),
    path('scraps/<str:plcy_no>/', ScrapDetailView.as_view(), name='scrap-detail'),
]