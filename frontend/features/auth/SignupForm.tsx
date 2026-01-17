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

  // ✅ 이메일 분리 (ID + 도메인)
  const [emailId, setEmailId] = useState("");
  const [emailDomain, setEmailDomain] = useState("gmail.com");
  const [isDirectDomain, setIsDirectDomain] = useState(false);

  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");

  // ✅ 정책 알림 수신 동의
  const [agreeNotification, setAgreeNotification] = useState(false);

  // ✅ 필드별 에러 상태 추가
  const [fieldErrors, setFieldErrors] = useState<{
    username?: string;
    password?: string;
    email?: string;
    non_field_errors?: string;
  }>({});

  const [loading, setLoading] = useState(false);

  // ✅ 도메인 변경 핸들러
  const handleDomainChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === "direct") {
      setIsDirectDomain(true);
      setEmailDomain("");
    } else {
      setIsDirectDomain(false);
      setEmailDomain(value);
    }
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldErrors({}); // 초기화

    // 1️⃣ 프론트 비밀번호 일치 검증
    if (password !== password2) {
      setFieldErrors((prev) => ({ ...prev, password: "❌ 비밀번호가 일치하지 않습니다." }));
      return;
    }

    // 2️⃣ 프론트 비밀번호 규칙 검증
    if (password.length < 8) {
      setFieldErrors((prev) => ({ ...prev, password: "❌ 비밀번호는 최소 8자 이상이어야 합니다." }));
      return;
    }

    // ✅ 이메일 조합
    const combinedEmail = emailId ? `${emailId}@${emailDomain}` : "";

    try {
      setLoading(true);

      await signup({
        username,
        email: combinedEmail || undefined,
        password,
        password2,
      });

      // 회원가입 성공 → 로그인 페이지로 이동
      alert("회원가입이 완료되었습니다! 로그인해주세요.");
      router.push("/login");
    } catch (err: any) {
      const errorData = err.response?.data;

      // ✅ 401 (토큰 만료)
      if (err.response?.status === 401) {
        setFieldErrors({ non_field_errors: "❌ 인증 정보가 만료되었습니다. 로그아웃 후 다시 시도해주세요." });
        return;
      }

      if (typeof errorData === "object") {
        // ✅ 백엔드 에러를 필드별로 매핑
        const newErrors: typeof fieldErrors = {};

        // 1. Username Error
        if (errorData.username) {
          const msg = errorData.username[0];
          if (msg.includes("already exists")) {
            newErrors.username = "❌ 이미 사용 중인 아이디입니다.";
          } else {
            newErrors.username = `❌ ${msg}`;
          }
        }

        // 2. Email Error
        if (errorData.email) {
          newErrors.email = `❌ ${errorData.email[0]}`; // 이메일 형식이 아닙니다 등
        }

        // 3. Password Error
        if (errorData.password) {
          let msg = errorData.password[0];
          if (msg.includes("too common")) msg = "❌ 너무 쉬운 비밀번호입니다.";
          else if (msg.includes("too short")) msg = "❌ 8자 이상이어야 합니다.";
          else if (msg.includes("numeric")) msg = "❌ 숫자로만 구성될 수 없습니다.";
          newErrors.password = msg;
        }

        // 4. 기타 에러
        if (!newErrors.username && !newErrors.email && !newErrors.password) {
          const messages = Object.values(errorData).flat();
          newErrors.non_field_errors = `❌ ${messages[0]}`;
        }

        setFieldErrors(newErrors);
      } else {
        setFieldErrors({ non_field_errors: "회원가입에 실패했습니다." });
      }
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
          className={`w-full rounded-md border px-3 py-2 text-sm ${fieldErrors.username ? 'border-red-500 bg-red-50' : ''}`}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="username"
          required
        />
        {/* ✅ 아이디 에러 메시지 위치 */}
        {fieldErrors.username && (
          <p className="text-[11px] font-medium text-red-600">{fieldErrors.username}</p>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm">이메일 (선택)</label>
        <div className="flex items-center gap-1">
          <input
            className={`w-full flex-1 rounded-md border px-3 py-2 text-sm ${fieldErrors.email ? 'border-red-500 bg-red-50' : ''}`}
            value={emailId}
            onChange={(e) => setEmailId(e.target.value)}
            placeholder="example"
          />
          <span className="text-gray-500">@</span>

          {isDirectDomain ? (
            <input
              className="w-1/3 rounded-md border px-3 py-2 text-sm"
              value={emailDomain}
              onChange={(e) => setEmailDomain(e.target.value)}
              placeholder="직접입력"
            />
          ) : (
            <select
              className="w-1/3 rounded-md border px-2 py-2 text-sm bg-white"
              onChange={handleDomainChange}
              defaultValue="gmail.com"
            >
              <option value="gmail.com">gmail.com</option>
              <option value="naver.com">naver.com</option>
              <option value="daum.net">daum.net</option>
              <option value="kakao.com">kakao.com</option>
              <option value="direct">직접입력</option>
            </select>
          )}
        </div>
        {fieldErrors.email && (
          <p className="text-[11px] font-medium text-red-600 pt-1">{fieldErrors.email}</p>
        )}

        {/* ✅ 정책 정보 알림 체크박스 */}
        <div className="flex items-center gap-2 pt-1">
          <input
            id="policy-noti"
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300"
            checked={agreeNotification}
            onChange={(e) => setAgreeNotification(e.target.checked)}
          />
          <label htmlFor="policy-noti" className="text-xs text-gray-700 select-none cursor-pointer">
            (선택) 정책정보 알림받기
          </label>
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm">비밀번호</label>
        <input
          className={`w-full rounded-md border px-3 py-2 text-sm ${fieldErrors.password ? 'border-red-500 bg-red-50' : ''}`}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          required
        />
        {fieldErrors.password && (
          <p className="text-[11px] font-medium text-red-600">
            {fieldErrors.password}
          </p>
        )}
        {/* ✅ 실시간 비밀번호 유효성 검사 메시지 */}
        {!(fieldErrors.password) && (
          password.length > 0 && password.length < 8 ? (
            <p className="text-[11px] text-red-500 font-medium">⚠️ 8자 이상 입력해주세요.</p>
          ) : (
            <p className="text-[11px] text-gray-600">* 영문, 숫자, 특수문자를 포함하여 8자 이상 입력해주세요.</p>
          )
        )}
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
        {/* ✅ 비밀번호 일치 시 성공 문구 */}
        {password && password2 && password === password2 && (
          <p className="text-[11px] text-green-600 font-medium">✓ 비밀번호가 일치합니다.</p>
        )}
      </div>

      {fieldErrors.non_field_errors && (
        <p className="text-sm font-medium text-red-600 break-keep text-center bg-red-50 p-2 rounded">
          {fieldErrors.non_field_errors}
        </p>
      )}

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
