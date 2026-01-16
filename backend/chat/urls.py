from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatSessionViewSet

# Router가 ViewSet의 URL 패턴 자동 생성
# - sessions/           → list, create
# - sessions/{id}/      → retrieve, update, destroy
# - sessions/{id}/send/ → 커스텀 액션 (메시지 전송)
router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='chat-session')

urlpatterns = [
    path('', include(router.urls)),
]
