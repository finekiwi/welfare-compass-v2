// services/axios.ts
import axios from "axios";
import { useAuthStore } from "@/stores/auth.store";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ✅ 메인 API 인스턴스 (인터셉터 포함)
export const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// ✅ 인터셉터 없는 Raw API 인스턴스 (logout 등 재귀 방지용)
export const apiRaw = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// ✅ Request Interceptor: 요청 보낼 때마다 토큰/CSRF 자동 주입
api.interceptors.request.use(
  (config) => {
    // CSRF 토큰 자동 주입 (쿠키에서 읽어서 헤더에 추가)
    if (typeof document !== "undefined") {
      const csrfToken = document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];

      if (csrfToken) {
        config.headers["X-CSRFToken"] = csrfToken;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ✅ Response Interceptor: 응답 에러 처리 (401 자동 갱신 지원)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 401 Unauthorized: 토큰 만료 또는 인증 실패
    // 원본 요청이 재시도(retry)된 적이 없는 경우에만 갱신 시도
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      // [보안] 무한 루프 방지: refresh/logout 엔드포인트의 401은 상태만 정리
      const guardUrls = ["/api/auth/token/refresh/", "/api/auth/logout/"];
      if (guardUrls.some(url => originalRequest.url?.includes(url))) {
        // 서버 logout 호출 없이 클라이언트 상태만 정리 (재귀 방지)
        useAuthStore.getState().clearAuth();
        return Promise.reject(error);
      }

      try {
        // 백엔드 TokenRefreshView 호출 (HttpOnly 쿠키 모드이므로 브라우저가 알아서 refresh_token 전송)
        await api.post("/api/auth/token/refresh/");

        // 토큰 갱신 성공 시 원래의 요청을 재시도
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh 토큰 만료 또는 없음 → 비로그인 상태로 처리 (정상 흐름)
        console.info("[Auth] 토큰 없음 또는 만료, 비로그인 상태로 초기화.");
        useAuthStore.getState().clearAuth();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
