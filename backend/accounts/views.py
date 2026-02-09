from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect # [추가] 리다이렉트를 위한 임포트
from policies.models import Policy
from .serializers import UserSerializer, ProfileSerializer, ScrapSerializer
from .models import Profile, Scrap
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings

# Google Login Imports
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

# [추가] 아이디 찾기를 위한 임포트
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView

class GoogleLogin(SocialLoginView):
    """
    구글 로그인 API
    
    프론트엔드에서 구글 로그인 후 받은 'code'를 이 API로 보내면,
    백엔드가 구글과 통신하여 제 3자 인증을 완료하고 JWT 토큰을 발급합니다.
    """
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:3000/api/auth/callback/google" # 프론트엔드 콜백 URL과 일치해야 함
    client_class = OAuth2Client


# class SignupView(generics.CreateAPIView):
#     """
#     회원가입 API
#     POST /api/accounts/signup/
#     """
#     queryset = User.objects.all()
#     authentication_classes = [] # ✅ 만료된 토큰이 있어도 무시하고 진행 (401 방지)
#     permission_classes = [AllowAny]
#     serializer_class = UserSerializer
#     
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()
#         
#         # 정책 알림 동의 정보를 Profile에 저장
#         email_notification_enabled = request.data.get('email_notification_enabled', False)
#         notification_email = request.data.get('notification_email', '')
#         
#         if email_notification_enabled:
#             profile = user.profile  # Profile은 signal로 자동 생성됨
#             profile.email_notification_enabled = True
#             profile.notification_email = notification_email or user.email
#             profile.save()
#         
#         return Response(
#             {
#                 "message": "회원가입이 완료되었습니다.",
#                 "user": {
#                     "username": user.username,
#                     "email": user.email
#                 }
#             },
#             status=status.HTTP_201_CREATED
#         )


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


# class CustomLoginView(TokenObtainPairView):
#     """
#     로그인 API (HttpOnly Cookie 설정)
#     """
#     def post(self, request, *args, **kwargs):
#         response = super().post(request, *args, **kwargs)
#         
#         if response.status_code == 200:
#             access_token = response.data.get('access')
#             refresh_token = response.data.get('refresh')
#             
#             # 쿠키 설정
#             response.set_cookie(
#                 'access_token',
#                 access_token,
#                 httponly=True,
#                 secure=False, 
#                 samesite='Lax',
#                 path='/',  # 명시적 경로 설정
#                 max_age=60 * 60 * 1, # 1시간
#             )
#             response.set_cookie(
#                 'refresh_token',
#                 refresh_token,
#                 httponly=True,
#                 secure=False,
#                 samesite='Lax',
#                 path='/',
#                 max_age=60 * 60 * 24 * 1, # 1일
#             )
#             
#             # 바디에서 토큰 제거
#             if 'access' in response.data:
#                 del response.data['access']
#             if 'refresh' in response.data:
#                 del response.data['refresh']
#             
#         return response
# 
# 
# class CustomRefreshView(TokenRefreshView):
#     """
#     토큰 갱신 API (Cookie에서 Refresh Token 읽기)
#     """
#     def post(self, request, *args, **kwargs):
#         # 쿠키에서 refresh token을 꺼내 data에 주입
#         if 'refresh' not in request.data:
#             refresh_token = request.COOKIES.get('refresh_token')
#             if refresh_token:
#                 request.data['refresh'] = refresh_token
#         
#         try:
#             response = super().post(request, *args, **kwargs)
#         except InvalidToken:
#             return Response({"detail": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
#         
#         if response.status_code == 200:
#             access_token = response.data.get('access')
#             
#             # Access Token 쿠키 갱신
#             response.set_cookie(
#                 'access_token',
#                 access_token,
#                 httponly=True,
#                 secure=False,
#                 samesite='Lax',
#                 path='/',
#                 max_age=60 * 60 * 1,
#             )
#             
#             # Refresh Token Rotation이 켜져있다면 Refresh Token도 갱신될 수 있음
#             if 'refresh' in response.data:
#                 refresh_token = response.data.get('refresh')
#                 response.set_cookie(
#                     'refresh_token',
#                     refresh_token,
#                     httponly=True,
#                     secure=False,
#                     samesite='Lax',
#                     path='/',
#                     max_age=60 * 60 * 24 * 1,
#                 )
#                 del response.data['refresh']
#             
#             if 'access' in response.data:
#                 del response.data['access']
#             
#         return response
# 
# 
# class LogoutView(generics.GenericAPIView):
#     """
#     로그아웃 API (쿠키 삭제)
#     """
#     permission_classes = [AllowAny]
# 
#     def post(self, request):
#         response = Response({"message": "로그아웃 되었습니다."}, status=status.HTTP_200_OK)
#         # set_cookie와 동일한 path, samesite 설정으로 삭제
#         response.delete_cookie('access_token', path='/', samesite='Lax')
#         response.delete_cookie('refresh_token', path='/', samesite='Lax')
#         return response


class FindUsernameView(APIView):
    """
    아이디 찾기 API
    POST /api/accounts/find-username/
    Body: { "email": "user@example.com" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        print("DEBUG: FindUsernameView POST received")
        email = request.data.get('email')
        print(f"DEBUG: Email received: {email}")
        
        if not email:
            return Response({"error": "이메일을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 이메일로 유저 찾기
        users = User.objects.filter(email=email)
        print(f"DEBUG: Users found: {users.count()}")
        
        if users.exists():
            # 2. 유저가 존재하면 이메일 발송
            user = users.first()
            subject = "[복지나침반] 아이디 찾기 결과입니다."
            message = f"회원님의 아이디는 '{user.username}' 입니다."
            
            try:
                print("DEBUG: Sending email...")
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                print("DEBUG: Email sent successfully")
            except Exception as e:
                # 로그 남기기 (실제 운영 시)
                print(f"DEBUG: Email send failed: {e}")
                pass
        else:
            print("DEBUG: User not found with this email")
        
        # 3. 보안을 위해 유저 존재 여부와 상관없이 성공 메시지 반환
        return Response(
            {"message": "입력하신 이메일로 아이디 정보를 전송했습니다."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmRedirectView(APIView):
    """
    비밀번호 재설정 이메일 링크 클릭 시 프론트엔드로 리다이렉트
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        # settings.FRONTEND_URL이 없으면 기본값 사용
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        redirect_url = f"{frontend_url}/auth/password-reset/confirm/{uidb64}/{token}"
        return HttpResponseRedirect(redirect_url)
