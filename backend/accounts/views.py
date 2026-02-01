from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from policies.models import Policy
from .serializers import UserSerializer, ProfileSerializer, ScrapSerializer
from .models import Profile, Scrap


class SignupView(generics.CreateAPIView):
    """
    회원가입 API
    POST /api/accounts/signup/
    """
    queryset = User.objects.all()
    authentication_classes = [] # ✅ 만료된 토큰이 있어도 무시하고 진행 (401 방지)
    permission_classes = [AllowAny]
    serializer_class = UserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "회원가입이 완료되었습니다.",
                "user": {
                    "username": user.username,
                    "email": user.email
                }
            },
            status=status.HTTP_201_CREATED
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    프로필 조회/수정 API
    GET  /api/accounts/profile/ - 내 프로필 조회
    PUT  /api/accounts/profile/ - 내 프로필 수정
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    
    def get_object(self):
        return self.request.user.profile

class ScrapListView(generics.ListAPIView):
    """내 스크랩 목록"""
    permission_classes = [IsAuthenticated]
    serializer_class = ScrapSerializer
    
    def get_queryset(self):
        return Scrap.objects.filter(user=self.request.user)


class ScrapDetailView(generics.GenericAPIView):
    """스크랩 추가/삭제"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, policy_id):  # [RENAME] plcy_no → policy_id
        """스크랩 추가"""
        policy = get_object_or_404(Policy, policy_id=policy_id)  # [RENAME] plcy_no → policy_id
        scrap, created = Scrap.objects.get_or_create(user=request.user, policy=policy)

        if created:
            return Response({"message": "스크랩되었습니다."}, status=status.HTTP_201_CREATED)
        return Response({"message": "이미 스크랩된 정책입니다."}, status=status.HTTP_200_OK)

    def delete(self, request, policy_id):  # [RENAME] plcy_no → policy_id
        """스크랩 삭제"""
        policy = get_object_or_404(Policy, policy_id=policy_id)  # [RENAME] plcy_no → policy_id
        deleted, _ = Scrap.objects.filter(user=request.user, policy=policy).delete()
        
        if deleted:
            return Response({"message": "스크랩이 취소되었습니다."}, status=status.HTTP_200_OK)
        return Response({"message": "스크랩되지 않은 정책입니다."}, status=status.HTTP_404_NOT_FOUND)