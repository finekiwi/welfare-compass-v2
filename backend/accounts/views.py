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
import os # [추가] 환경변수 접근용
from django.conf import settings

# Google Login Imports
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

# [추가] 아이디 찾기를 위한 임포트
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView

# [추가] 계정 잠금 (dj-rest-auth LoginView 커스텀)
from dj_rest_auth.views import LoginView as DjRestAuthLoginView
from axes.models import AccessAttempt
from django.utils import timezone
from datetime import timedelta


import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["POST"])
def clean_logout(request):
    """
    쿠키 완전 삭제 로그아웃.
    [주의] Python SimpleCookie는 쿠키 이름을 KEY로 쓰는 딕셔너리라,
    같은 이름으로 delete_cookie를 두 번 호출하면 마지막 것이 앞 것을 덮어씀.
    SIMPLE_JWT.AUTH_COOKIE_PATH='/'로 통일되어 있으므로 Path=/ 하나만 삭제하면 됨.
    """
    response = HttpResponse(
        json.dumps({"detail": "로그아웃 되었습니다."}),
        content_type='application/json',
        status=200,
    )

    # access_token 삭제 (Path=/)
    response.delete_cookie('access_token', path='/', samesite='Lax')

    # refresh_token 삭제 (Path=/ — dj-rest-auth와 simplejwt 모두 이제 / 사용)
    response.delete_cookie('refresh_token', path='/', samesite='Lax')

    return response


# urls.py에서 CleanLogoutView 대신 clean_logout 을 참조해야 함
CleanLogoutView = clean_logout  # 하위 호환 alias


class AxesLockedLoginView(DjRestAuthLoginView):
    """
    dj-rest-auth LoginView + 계정 잠금

    dj-rest-auth의 LoginSerializer는 내부적으로 인증 실패를 처리(400)하므로,
    django-axes의 인증 백엔드가 실패를 감지하지 못합니다.

    이 뷰는 직접 AccessAttempt 테이블을 관리합니다:
    1. 로그인 전: 잠금 상태 확인 → 잠김이면 403 반환
    2. 로그인 실패 시: 실패 횟수 +1 기록 → 한도 도달 시 403 반환
    3. 로그인 성공 시: 실패 기록 초기화
    """

    def _get_lockout_config(self):
        cooloff = getattr(settings, 'AXES_COOLOFF_TIME', timedelta(minutes=5))
        limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        return cooloff, limit

    def _is_locked(self, username):
        """username이 잠금 상태인지 확인"""
        cooloff, limit = self._get_lockout_config()
        threshold = timezone.now() - cooloff
        return AccessAttempt.objects.filter(
            username=username,
            failures_since_start__gte=limit,
            attempt_time__gte=threshold,
        ).exists()

    def _record_failure(self, request, username):
        """로그인 실패 기록"""
        ip = self._get_client_ip(request)
        attempt, created = AccessAttempt.objects.get_or_create(
            username=username,
            defaults={
                'ip_address': ip,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
                'attempt_time': timezone.now(),
                'failures_since_start': 1,
            }
        )
        if not created:
            attempt.failures_since_start += 1
            attempt.attempt_time = timezone.now()
            attempt.save(update_fields=['failures_since_start', 'attempt_time'])
        return attempt.failures_since_start

    def _reset_failures(self, username):
        """로그인 성공 시 실패 기록 초기화"""
        AccessAttempt.objects.filter(username=username).delete()

    def _get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')

    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')

        if username and self._is_locked(username):
            return Response(
                {"error": "로그인 시도가 너무 많습니다. 5분 후 다시 시도해주세요."},
                status=status.HTTP_403_FORBIDDEN,
            )

        response = super().post(request, *args, **kwargs)

        if username:
            if response.status_code == 400:
                # 로그인 실패 → 실패 횟수 기록
                _, limit = self._get_lockout_config()
                failures = self._record_failure(request, username)
                if failures >= limit:
                    return Response(
                        {"error": "로그인 시도가 너무 많습니다. 5분 후 다시 시도해주세요."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            elif response.status_code == 200:
                # 로그인 성공 → 실패 기록 초기화
                self._reset_failures(username)

        return response

class GoogleLogin(SocialLoginView):
    """
    구글 로그인 API
    
    프론트엔드에서 구글 로그인 후 받은 'code'를 이 API로 보내면,
    백엔드가 구글과 통신하여 제 3자 인증을 완료하고 JWT 토큰을 발급합니다.
    """
    adapter_class = GoogleOAuth2Adapter
    callback_url = "postmessage" # 프론트엔드 Popup Flow(postmessage) 사용 시 필수
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        print("DEBUG: GoogleLogin POST received")
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Google Login Exception: {e}", exc_info=True)
            return Response({"error": "구글 로그인 처리에 실패했습니다. 잠시 후 다시 시도해주세요."}, status=status.HTTP_400_BAD_REQUEST)


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


import requests
from dj_rest_auth.views import PasswordResetView # [추가] 부모 클래스 임포트

def verify_recaptcha(token):
    """Google reCAPTCHA v2 검증"""
    secret_key = os.environ.get('RECAPTCHA_SECRET_KEY')
    # [보안] 운영 환경(DEBUG=False)에서는 키 누락 시 무조건 차단
    if not secret_key:
        if not settings.DEBUG:
            logger.error("RECAPTCHA_SECRET_KEY가 설정되지 않았습니다. 운영 환경에서는 필수입니다.")
            return False
        return True  # 개발 환경에서만 패스
        
    if not token:
        return False
        
    data = {
        'secret': secret_key,
        'response': token
    }
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            timeout=5,  # [보안] 구글 API 지연 시 스레드 행(hang) 방지
        )
        result = response.json()
        return result.get('success', False)
    except requests.exceptions.Timeout:
        logger.warning("reCAPTCHA 검증 API 타임아웃 발생")
        return False
    except Exception:
        return False

class CustomPasswordResetView(PasswordResetView):
    """
    비밀번호 재설정 API (reCAPTCHA + User Enumeration 방지)
    """
    def post(self, request, *args, **kwargs):
        # 0. reCAPTCHA 검증
        token = request.data.get('recaptchaToken')
        if not verify_recaptcha(token):
            return Response({"error": "로봇이 아님을 증명해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        
        # [보안] User Enumeration 방지: 이메일 존재 여부와 무관하게 동일한 200 응답 반환
        if not User.objects.filter(email=email).exists():
            logger.info("비밀번호 재설정 요청 - 미가입 이메일")
            return Response(
                {"detail": "입력하신 이메일이 가입된 계정이라면, 비밀번호 재설정 링크를 발송했습니다."},
                status=status.HTTP_200_OK
            )
            
        return super().post(request, *args, **kwargs)


import logging

logger = logging.getLogger(__name__)

class FindUsernameView(APIView):
    """
    아이디 찾기 API (reCAPTCHA + User Enumeration 방지)
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # 0. reCAPTCHA 검증
        token = request.data.get('recaptchaToken')
        if not verify_recaptcha(token):
            return Response({"error": "로봇이 아님을 증명해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        
        if not email:
            return Response({"error": "이메일을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # [보안] User Enumeration 방지: 가입 여부와 관계없이 동일한 응답 반환
        # 실제 발송은 가입자에게만 처리
        UNIFIED_MESSAGE = "입력하신 이메일이 가입된 계정이라면, 아이디 정보를 발송했습니다."

        users = User.objects.filter(email=email)
        
        if not users.exists():
            logger.info(f"아이디 찾기 요청 - 미가입 이메일")
            return Response(
                {"message": UNIFIED_MESSAGE},
                status=status.HTTP_200_OK
            )

        # 유저가 존재하면 이메일 발송
        user = users.first()
        subject = "[복지나침반] 아이디 찾기 결과입니다."
        message = f"회원님의 아이디는 '{user.username}' 입니다."
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            # 이메일 마스킹 로직
            masked_email = email
            if '@' in email:
                local, domain = email.split('@')
                if len(local) > 3:
                    masked_email = f"{local[:3]}***@{domain}"
                else:
                    masked_email = f"{local}***@{domain}"
            
            logger.info(f"아이디 찾기 이메일 발송 성공: {masked_email}")

        except Exception as e:
            logger.error(f"이메일 발송 실패: {e}")
            pass
        
        return Response(
            {"message": UNIFIED_MESSAGE},
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
