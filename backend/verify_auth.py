import requests
import json
import random
import string

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    # 1. 세션 생성 (쿠키 자동 관리)
    session = requests.Session()
    
    # 랜덤 유저 생성
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    username = f"testuser_{suffix}"
    password = "TestPassword123!"
    email = f"test_{suffix}@example.com"
    
    print(f"------- 1. Login Test (User: {username}) -------")
    
    # 회원가입 시도
    # Serializer에 따르면 required fields: username, email, password, password2
    signup_data = {
        "username": username,
        "password1": password,
        "password2": password,
        "email": email
    }
    
    try:
        # [Modify] API 엔드포인트 변경
        signup_resp = session.post(f"{BASE_URL}/api/auth/registration/", json=signup_data)
        print(f"Signup Status: {signup_resp.status_code}")
        if signup_resp.status_code != 201:
            print("Signup Failed Details:", signup_resp.text)
    except Exception as e:
        print(f"Signup failed (maybe exists): {e}")

    # 로그인
    # [Modify] API 엔드포인트 변경
    login_resp = session.post(f"{BASE_URL}/api/auth/login/", json={
        "username": username,
        "password": password,
        # "email": email # dj-rest-auth는 username/password 기본 (설정에 따름)
    })
    
    print(f"Login Status: {login_resp.status_code}")
    if login_resp.status_code == 200:
        print("Login Success")
        print("Cookies:", session.cookies.get_dict())
        if 'access_token' in session.cookies:
            print("✅ Access Token Cookie found")
        else:
            print("❌ Access Token Cookie NOT found")
    else:
        print("Login Failed:", login_resp.text)
        return

    print("\n------- 2. Protected Resource Test (Profile) -------")
    # [Keep] Profile은 기존 커스텀 View 사용 (여전히 쿠키 인증 작동해야 함)
    profile_resp = session.get(f"{BASE_URL}/api/accounts/profile/")
    print(f"Profile Status: {profile_resp.status_code}")
    if profile_resp.status_code == 200:
        print("✅ Profile Access Success (via Cookie)")
        print("Profile Data:", profile_resp.json())
    else:
        print("❌ Profile Access Failed")
    
    print("\n------- 3. Logout Test -------")
    # [Modify] API 엔드포인트 변경
    logout_resp = session.post(f"{BASE_URL}/api/auth/logout/")
    print(f"Logout Status: {logout_resp.status_code}")
    
    # 쿠키가 삭제되었는지 확인 (requests session에서는 expired cookie가 사라짐)
    # Logout API에서 delete_cookie를 호출하면, 응답 헤더에 Set-Cookie ... Expires=... 가 옴
    # requests는 이를 처리하여 session.cookies에서 제거해야 함
    print("Cookies after logout:", session.cookies.get_dict())
    if 'access_token' not in session.cookies.get_dict():
        print("✅ Access Token Cookie cleared")
    else:
        print("❌ Access Token Cookie still exists")

    print("\n------- 4. Access after Logout -------")
    profile_resp_2 = session.get(f"{BASE_URL}/api/accounts/profile/")
    print(f"Profile Status: {profile_resp_2.status_code}")
    if profile_resp_2.status_code == 401:
        print("✅ Access Denied (Correct)")
    else:
        print("❌ Access Allowed (Incorrect)")

if __name__ == "__main__":
    test_auth_flow()
