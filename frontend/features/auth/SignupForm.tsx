"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signup } from "./auth.api";

/**
 * SignupForm
 * - 백엔드 UserSerializer 요구사항(username/email/password/password2)에 맞춰 폼 구성
 * - 비밀번호 일치 검증은 프론트에서도 1차로 하고, 최종 검증은 백엔드가 책임
 *   (백엔드에서 validate로 password/password2 비교) :contentReference[oaicite:5]{index=5}
 */
export function SignupForm() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(""); // 선택값으로 취급 가능
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // 프론트 1차 검증(UX)
    if (password !== password2) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    try {
      setLoading(true);

      await signup({
        username,
        email: email || undefined,
        password,
        password2,
      });

      // 회원가입 성공 → 로그인 페이지로 이동
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "회원가입에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-sm space-y-4 rounded-xl border p-6">
      <h1 className="text-lg font-semibold">회원가입</h1>

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
        <label className="text-sm">이메일 (선택)</label>
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email@example.com"
          type="email"
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

      <div className="space-y-2">
        <label className="text-sm">비밀번호 확인</label>
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          value={password2}
          onChange={(e) => setPassword2(e.target.value)}
          type="password"
          required
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        className="w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        disabled={loading}
      >
        {loading ? "처리 중..." : "회원가입"}
      </button>

      <p className="text-xs text-gray-500">
        이미 계정이 있나요? <a className="underline" href="/login">로그인</a>
      </p>
    </form>
  );
}
