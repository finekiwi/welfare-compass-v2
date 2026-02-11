// features/auth/auth.api.ts
import { api } from "@/services/axios";
import type { LoginRequest, LoginResponse, SignupRequest, SignupResponse } from "./auth.types";

/**
 * ✅ 회원가입 API
 */
export async function signup(payload: SignupRequest): Promise<SignupResponse> {
  const response = await api.post<SignupResponse>("/api/auth/registration/", payload);
  return response.data;
}

/**
 * ✅ 로그인 API
 */
export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>("/api/auth/login/", payload);
  // 쿠키는 브라우저가 자동 처리
  return response.data;
}

/**
 * ✅ 토큰 갱신 API
 */
export async function refreshToken(refresh: string): Promise<{ access: string }> {
  const response = await api.post<{ access: string }>("/api/auth/token/refresh/", { refresh });
  return response.data;
}
/**
 * ✅ 로그아웃 API
 */
export async function logout(): Promise<void> {
  await api.post("/api/auth/logout/");
}

/**
 * ✅ 구글 로그인 API
 * @param code 구글에서 받은 인가 코드
 */
export async function loginWithGoogle(code: string): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>("/api/auth/google/login/", {
    code,
    // Note: dj-rest-auth의 SocialLoginView는 code를 받아서 처리함
  });
  return response.data;
}

/**
 * ✅ 이메일 인증 확인 API
 * @param key 이메일로 받은 인증 키
 */
export async function verifyEmail(key: string): Promise<void> {
  await api.post("/api/auth/registration/verify-email/", { key });
}

/**
 * ✅ 아이디 찾기 API (이메일 발송)
 */
export async function findUsername(email: string, recaptchaToken?: string | null): Promise<void> {
  await api.post("/api/auth/find/username/", { email, recaptchaToken });
}

/**
 * ✅ 비밀번호 재설정 요청 (이메일 발송)
 */
export async function requestPasswordReset(email: string, recaptchaToken?: string | null): Promise<void> {
  await api.post("/api/auth/password/reset/", { email, recaptchaToken });
}

/**
 * ✅ 비밀번호 재설정 확정
 */
export async function confirmPasswordReset(data: any): Promise<void> {
  await api.post("/api/auth/password/reset/confirm/", data);
}
