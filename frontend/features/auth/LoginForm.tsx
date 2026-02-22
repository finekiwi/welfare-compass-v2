"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "./auth.api";
import { useAuthStore } from "@/stores/auth.store";
import GoogleLoginButton from "./components/GoogleLoginButton";

/**
 * LoginForm
 * - simplejwt TokenObtainPairView: username/password → access/refresh 반환
 * - 전역 auth store를 통해 토큰 저장 및 인증 상태 관리
 */
export function LoginForm() {
  const router = useRouter();
  const authLogin = useAuthStore((state) => state.login);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      setLoading(true);

      await login({ username, password });

      // ✅ 쿠키 검증 후 인증 상태 확정 (보수적 업데이트)
      await authLogin();

      // 로그인 성공 후 메인 페이지로 이동
      router.push("/");
    } catch (err: any) {
      console.error("Login Error:", err);
      // 백엔드 에러 원인에 따른 한글 메시지 처리
      if (err.response?.status === 401) {
        // "Given token not valid..." 포함한 토큰 에러 처리
        if (JSON.stringify(err.response?.data).includes("token_not_valid")) {
          setError("❌ 인증 정보가 만료되었습니다. 다시 시도해주세요.");
        } else {
          setError("❌ 아이디 또는 비밀번호가 일치하지 않습니다.");
        }
      } else if (err.response?.status === 400) {
        const data = err.response?.data;
        if (data && data.non_field_errors) {
          // dj-rest-auth는 잘못된 로그인 자격증명에 400 + non_field_errors를 반환함
          setError("❌ 아이디 또는 비밀번호가 일치하지 않습니다.");
        } else {
          setError("❌ 입력 정보를 다시 확인해주세요.");
        }
      } else {
        setError("❌ 로그인에 실패했습니다. 5분 후 다시 시도해주세요.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-sm space-y-4 rounded-xl border p-6">
      <h1 className="text-lg font-semibold">로그인</h1>

      <div className="space-y-2">
        <label className="text-sm">아이디</label>
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="username"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm">비밀번호</label>
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          required
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        className="w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        disabled={loading}
      >
        {loading ? "처리 중..." : "로그인"}
      </button>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-2 text-gray-500">Or continue with</span>
        </div>
      </div>

      <GoogleLoginButton />

      <div className="flex justify-between items-center text-xs text-gray-500 mt-4">
        <a className="hover:underline" href="/auth/find">아이디/비밀번호 찾기</a>
        <p>
          아직 계정이 없나요? <a className="underline font-medium ml-1" href="/signup">회원가입</a>
        </p>
      </div>
    </form>
  );
}
