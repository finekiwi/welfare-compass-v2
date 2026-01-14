"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "./auth.api";

/**
 * LoginForm
 * - simplejwt TokenObtainPairView: username/password → access/refresh 반환 :contentReference[oaicite:6]{index=6}
 * - 데모 구현: localStorage에 저장
 *   (실서비스에서는 httpOnly cookie + 서버에서 토큰 관리가 더 안전)
 */
export function LoginForm() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      setLoading(true);

      const tokens = await login({ username, password });

      // ✅ 토큰 저장 (간단 버전)
      localStorage.setItem("access_token", tokens.access);
      localStorage.setItem("refresh_token", tokens.refresh);

      // 로그인 성공 후 마이페이지로 보내는 예시
      router.push("/mypage");
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인에 실패했습니다.");
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

      <p className="text-xs text-gray-500">
        아직 계정이 없나요? <a className="underline" href="/signup">회원가입</a>
      </p>
    </form>
  );
}
