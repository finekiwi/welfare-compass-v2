// features/auth/auth.api.ts
// fetch 기반 API 모듈 (axios로 바꿔도 구조는 그대로 유지 가능)

import type { LoginRequest, LoginResponse, SignupRequest, SignupResponse } from "./auth.types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

// 공통: JSON 요청 헬퍼
async function postJSON<TResponse>(url: string, body: unknown): Promise<TResponse> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // 필요하면 credentials 옵션(쿠키 인증 등)도 여기서 통일
    body: JSON.stringify(body),
  });

  // DRF는 에러 시 detail / field errors 형태가 많아서
  // 실패면 JSON을 읽어 메시지로 던져주는 패턴이 디버깅에 좋아요.
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    // 가능한 에러 메시지를 최대한 살려서 던짐
    const message =
      data?.message ||
      data?.detail ||
      (typeof data === "object" ? JSON.stringify(data) : "요청에 실패했습니다.");
    throw new Error(message);
  }

  return data as TResponse;
}

export function signup(payload: SignupRequest) {
  return postJSON<SignupResponse>(`${BASE}/api/accounts/signup/`, payload);
}

export function login(payload: LoginRequest) {
  // TokenObtainPairView: username/password를 받음
  return postJSON<LoginResponse>(`${BASE}/api/accounts/login/`, payload);
}

export function refreshToken(refresh: string) {
  return postJSON<{ access: string }>(`${BASE}/api/accounts/token/refresh/`, { refresh });
}
