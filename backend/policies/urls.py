from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PolicyViewSet

router = DefaultRouter()
router.register(r'', PolicyViewSet, basename='policy')  # [FIX] 중복 prefix 제거 (config/urls.py에서 이미 'api/policies/' 사용)

urlpatterns = [
    path('', include(router.urls)),
]