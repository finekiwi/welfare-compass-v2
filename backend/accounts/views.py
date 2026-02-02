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
        
        # 정책 알림 동의 정보를 Profile에 저장
        email_notification_enabled = request.data.get('email_notification_enabled', False)
        notification_email = request.data.get('notification_email', '')
        
        if email_notification_enabled:
            profile = user.profile  # Profile은 signal로 자동 생성됨
            profile.email_notification_enabled = True
            profile.notification_email = notification_email or user.email
            profile.save()
        
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


class CheckUsernameView(generics.GenericAPIView):
    """
    아이디 중복 확인 API
    GET /api/accounts/check-username/?username=xxx
    
    Returns:
        - available: true/false
        - message: 사용 가능 여부 메시지
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def get(self, request):
        username = request.query_params.get('username', '').strip()
        
        if not username:
            return Response(
                {"available": False, "message": "아이디를 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 최소 길이 체크
        if len(username) < 3:
            return Response(
                {"available": False, "message": "아이디는 3자 이상이어야 합니다."},
                status=status.HTTP_200_OK
            )
        
        # 중복 체크
        if User.objects.filter(username=username).exists():
            return Response(
                {"available": False, "message": "이미 사용 중인 아이디입니다."},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {"available": True, "message": "사용 가능한 아이디입니다."},
            status=status.HTTP_200_OK
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
        # Profile이 없는 기존 유저의 경우 자동 생성
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

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


class DeleteAccountView(generics.GenericAPIView):
    """
    회원탈퇴 API
    DELETE /api/accounts/delete/
    
    Request Body:
        - password: 현재 비밀번호 (확인용)
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        password = request.data.get('password')
        
        if not password:
            return Response(
                {"error": "비밀번호를 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # 비밀번호 확인
        if not user.check_password(password):
            return Response(
                {"error": "비밀번호가 일치하지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 사용자 삭제 (CASCADE로 Profile, Scrap 등 자동 삭제)
        username = user.username
        user.delete()
        
        return Response(
            {"message": f"'{username}' 계정이 삭제되었습니다. 이용해주셔서 감사합니다."},
            status=status.HTTP_200_OK
        )