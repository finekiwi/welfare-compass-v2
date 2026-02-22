# 🚀 배포 시 인증/로그인 체크리스트

> 로컬 개발 환경과 다르게 운영 서버에서 반드시 설정해야 할 항목들을 정리합니다.

---

## 1. 환경변수 (`.env` 또는 서버 환경변수)

| 변수명 | 로컬 값 | 운영 서버 설정 | 필수 여부 |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | 임시 insecure 키 | **무작위 50자 이상 고유 키** | ✅ 필수 |
| `DJANGO_DEBUG` | `True` | **설정 자체를 제거** (기본값 False) | ✅ 필수 |
| `DJANGO_DB_PASSWORD` | 로컬 DB 비밀번호 | 운영 DB 비밀번호 | ✅ 필수 |
| `RECAPTCHA_SECRET_KEY` | 테스트 키 또는 없음 | **Google Console에서 발급한 운영 키** | ✅ 필수 |
| `GOOGLE_CLIENT_ID` | 개발용 OAuth ID | 운영 도메인 등록된 OAuth ID | ✅ 필수 |
| `GOOGLE_CLIENT_SECRET` | 개발용 시크릿 | 운영용 시크릿 | ✅ 필수 |
| `EMAIL_HOST_USER` | Gmail 주소 | 동일 또는 운영용 메일 | ✅ 필수 |
| `EMAIL_HOST_PASSWORD` | 앱 비밀번호 | 동일 또는 운영용 비밀번호 | ✅ 필수 |
| `FRONTEND_URL` | `http://localhost:3000` | **`https://your-domain.com`** | ✅ 필수 |

### SECRET_KEY 생성 방법
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 2. Django `settings.py` 추가 설정

`DEBUG=False`로 전환 시 **자동 적용** 되는 것:
- `JWT_AUTH_SECURE = True` (쿠키에 Secure 속성 자동 적용)
- 상세 에러 페이지 비활성화
- insecure SECRET_KEY로 서버 기동 차단

**직접 추가해야 하는 것** — 운영 전용 블록을 `settings.py` 하단에 추가:

```python
# ===== 운영 환경 전용 설정 (DEBUG=False 일 때만 활성화) =====
if not DEBUG:
    # HTTPS 전용 쿠키
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

    # HTTPS로 강제 리다이렉트 (서버에서 HTTPS 처리하는 경우 True)
    SECURE_SSL_REDIRECT = True          # nginx/ALB에서 SSL 처리 시 False로 변경
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # 프록시 뒤 배포 시

    # HSTS (브라우저가 HTTPS만 사용하도록 강제)
    SECURE_HSTS_SECONDS = 31536000     # 1년
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    # 허용 도메인
    ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

    # CORS
    CORS_ALLOWED_ORIGINS = ['https://your-domain.com']
    CSRF_TRUSTED_ORIGINS = ['https://your-domain.com']
```

---

## 3. Google OAuth 설정 (Google Cloud Console)

1. **OAuth 동의 화면** → 앱 도메인: 운영 도메인으로 변경
2. **OAuth 2.0 클라이언트** → 승인된 JavaScript 출처에 `https://your-domain.com` 추가
3. **승인된 리다이렉션 URI**: `https://your-domain.com/api/auth/google/login/callback/` 추가
4. **reCAPTCHA** → 사이트 도메인에 운영 도메인 추가 (localhost 제거)

---

## 4. Django 마이그레이션

배포 서버에서 반드시 실행:

```bash
python manage.py migrate                      # DB 스키마 적용
python manage.py createcachetable             # (캐시 사용 시)
python manage.py collectstatic --noinput      # 정적 파일 수집
```

---

## 5. Django-axes (로그인 잠금) 설정 확인

`settings.py`에서 운영 환경에 맞게 조정:

```python
AXES_FAILURE_LIMIT = 5          # 로그인 실패 허용 횟수 (현재 5회)
AXES_COOLOFF_TIME = timedelta(minutes=5)  # 잠금 해제 시간

# 운영 권장: IP+username 복합 잠금 (현재 username만 — 향후 개선 과제)
# AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
```

---

## 6. 이메일 설정 확인

`DEBUG=False` 시 자동으로 Gmail SMTP로 전환됩니다. 발송 전 확인:

```bash
# 테스트 이메일 발송
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('테스트', '본문', 'from@example.com', ['to@example.com'])
"
```

---

## 7. 프론트엔드 환경변수 (`.env.production`)

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
NEXT_PUBLIC_RECAPTCHA_SITE_KEY=운영용_사이트_키
```

---

## 8. 배포 후 검증 체크리스트

- [ ] 일반 로그인/로그아웃 동작 확인
- [ ] 로그아웃 후 쿠키 완전 삭제 확인 (DevTools → Application → Cookies)
- [ ] Access Token 만료 후 자동 갱신 확인 (Network 탭)
- [ ] reCAPTCHA 동작 확인 (운영 도메인에서 테스트)
- [ ] Google OAuth 로그인 확인
- [ ] 로그인 5회 실패 후 잠금 → 5분 후 해제 확인
- [ ] 비밀번호 찾기 이메일 수신 확인
- [ ] HTTPS 강제 리다이렉트 확인 (`http://` 접속 시 `https://`로 이동)
- [ ] `DEBUG=False` 상태에서 에러 페이지가 상세 정보를 노출하지 않는지 확인
