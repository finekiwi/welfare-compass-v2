// services/axios.ts
import axios from "axios";

// ✅ 나중에 baseURL을 환경변수로 교체하세요.
// 예: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  withCredentials: true,
});
