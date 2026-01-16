// services/axios.ts
import axios from "axios";

// ✅ baseURL 설정
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// ✅ Request Interceptor: 요청 보낼 때마다 토큰 자동 주입
api.interceptors.request.use(
  (config) => {
    // 서버 사이드 렌더링(SSR) 중에는 localStorage 접근 불가하므로 체크
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`; // JWT 표준
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ✅ Response Interceptor: 응답 에러 처리 (로그아웃 등)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // 401 Unauthorized: 토큰 만료 또는 인증 실패
    if (error.response?.status === 401) {
      // TODO: Refresh Token 로직 구현 가능
      // 지금은 간단히 로그아웃 처리 (토큰 삭제)
      if (typeof window !== "undefined") {
        // localStorage.removeItem("access_token");
        // localStorage.removeItem("refresh_token");
        // window.location.href = "/login"; // 강제 이동 (선택사항)
      }
    }
    return Promise.reject(error);
  }
);
