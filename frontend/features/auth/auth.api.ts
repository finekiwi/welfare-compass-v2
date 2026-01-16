// features/auth/auth.api.ts
import { api } from "@/services/axios";
import type { LoginRequest, LoginResponse, SignupRequest, SignupResponse } from "./auth.types";

/**
 * ✅ 회원가입 API
 */
export async function signup(payload: SignupRequest): Promise<SignupResponse> {
  const response = await api.post<SignupResponse>("/api/accounts/signup/", payload);
  return response.data;
}

/**
 * ✅ 로그인 API
 */
export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>("/api/accounts/login/", payload);
  return response.data;
}

/**
 * ✅ 토큰 갱신 API
 */
export async function refreshToken(refresh: string): Promise<{ access: string }> {
  const response = await api.post<{ access: string }>("/api/accounts/token/refresh/", { refresh });
  return response.data;
}
