"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "./auth.api";
import { useAuthStore } from "@/stores/auth.store";
import GoogleLoginButton from "./components/GoogleLoginButton";

interface LoginFormProps {
  embedded?: boolean;
}

export function LoginForm({ embedded = false }: LoginFormProps) {
  const router = useRouter();
  const authLogin = useAuthStore((state) => state.login);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    try {
      setLoading(true);
      await login({ username, password });
      await authLogin();
      router.push("/");
    } catch (err: any) {
      console.error("Login Error:", err);
      console.error("Login Error Detail:", {
        status: err?.response?.status,
        url: err?.config?.url,
        data: err?.response?.data,
      });
      console.error("Login Error Data JSON:", JSON.stringify(err?.response?.data));
      if (err.response?.status === 401) {
        if (JSON.stringify(err.response?.data).includes("token_not_valid")) {
          setError("인증 정보가 만료되었습니다. 다시 시도해주세요.");
        } else {
          setError("아이디 또는 비밀번호가 일치하지 않습니다.");
        }
      } else if (err.response?.status === 400) {
        const data = err.response?.data;
        if (data && data.non_field_errors) {
          const msg = String(data.non_field_errors?.[0] ?? "");
          if (msg.toLowerCase().includes("e-mail is not verified") || msg.toLowerCase().includes("email is not verified")) {
            setError("이메일 인증을 완료해주세요. 인증 메일을 확인해주세요.");
          } else {
            setError("아이디 또는 비밀번호가 일치하지 않습니다.");
          }
        } else {
          setError("입력 정보를 다시 확인해주세요.");
        }
      } else {
        setError("로그인에 실패했습니다. 잠시 후 다시 시도해주세요.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className={[
        "w-full",
        embedded ? "space-y-4" : "mx-auto max-w-sm space-y-4 rounded-xl border border-gray-300 bg-white p-6",
      ].join(" ")}
    >
      <h1 className="pt-1 text-[18px] font-bold leading-none text-gray-800">로그인</h1>

      <div>
        <input
          className="h-9 w-full rounded-md border border-gray-300 px-3 text-[15px] outline-none focus:border-gray-500"
          placeholder="아이디"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
        />
      </div>

      <div>
        <input
          className="h-9 w-full rounded-md border border-gray-300 px-3 text-[15px] outline-none focus:border-gray-500"
          placeholder="비밀번호"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          type="password"
          required
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        className="h-9 w-full rounded-md bg-[#8F8F8F] text-base font-semibold text-white disabled:opacity-60"
        disabled={loading}
      >
        {loading ? "처리 중..." : "로그인"}
      </button>

      <div className="relative pt-1">
        <div className="absolute inset-0 top-4 flex items-center">
          <span className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-3 text-gray-500">OR CONTINUE WITH</span>
        </div>
      </div>

      <GoogleLoginButton />

      <div className="mt-1 flex items-center justify-between text-[13px] text-gray-500">
        <a className="hover:underline" href="/auth/find">
          아이디/비밀번호 찾기
        </a>
        <p>
          아직 계정이 없나요?
          <a className="ml-1 font-semibold underline" href="/signup">
            회원가입
          </a>
        </p>
      </div>
    </form>
  );
}
