"use client";

import Link from "next/link";
import Image from "next/image";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { LoginForm } from "@/features/auth/LoginForm";
import { HeroBanner } from "@/features/home/HeroBanner";
import { ChatMessageBubble } from "@/features/chatbot/ChatMessage";
import { ThinkingIndicator } from "@/features/chatbot/ThinkingIndicator";
import { JOB_STATUS_LABELS, HOUSING_TYPE_LABELS } from "@/features/chatbot/chatbot.labels";
import { clearLocalAvatarUrl, saveLocalAvatarUrl } from "@/features/mypage/mypage.api";
import { useAuthStore } from "@/stores/auth.store";
import { useChatbotStore } from "@/stores/chatbot.store";
import { useProfileStore } from "@/stores/profile.store";

const QUICK_TAGS = ["취준생", "월세", "청년", "저소득", "전세", "출산/육아"];

export function HomeLoginChatSection() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const profile = useProfileStore((s) => s.profile);
  const fetchProfile = useProfileStore((s) => s.fetchProfile);
  const updateProfile = useProfileStore((s) => s.updateProfile);
  const isLoading = useChatbotStore((s) => s.isLoading);
  const sessionId = useChatbotStore((s) => s.sessionId);
  const messages = useChatbotStore((s) => s.messages);
  const ensureSession = useChatbotStore((s) => s.ensureSession);
  const refreshSession = useChatbotStore((s) => s.refreshSession);
  const sendMessage = useChatbotStore((s) => s.sendMessage);
  const open = useChatbotStore((s) => s.open);
  const hasProfileData = useChatbotStore((s) => s.hasProfileData);
  const profileInjected = useChatbotStore((s) => s.profileInjected);
  const setProfileInjected = useChatbotStore((s) => s.setProfileInjected);
  const [text, setText] = useState("");
  const [showProfileInfo, setShowProfileInfo] = useState(true);
  const avatarInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isAuthenticated && !profile) {
      void fetchProfile();
    }
  }, [fetchProfile, isAuthenticated, profile]);

  // 세션이 없으면 자동 생성 → 백엔드 인사말을 단일 소스로 사용
  // sessionId가 null이 되면(로그인/로그아웃 리셋 시) 다시 세션 생성
  useEffect(() => {
    if (!sessionId) {
      void ensureSession();
    }
  }, [sessionId, ensureSession]);

  const visibleMessages = useMemo(() => messages.slice(-5), [messages]);

  const age = useMemo(() => {
    if (!profile?.birthYear) return "-";
    return `만 ${new Date().getFullYear() - profile.birthYear}세`;
  }, [profile?.birthYear]);

  const profileRows = useMemo(
    () => [
      { label: "거주지", value: profile?.district || "-" },
      { label: "나이", value: age },
      { label: "주거 형태", value: profile?.housingType ? HOUSING_TYPE_LABELS[profile.housingType] || "-" : "-" },
      { label: "취업 상태", value: profile?.jobStatus ? JOB_STATUS_LABELS[profile.jobStatus] || "-" : "-" },
      { label: "연 소득", value: profile?.incomeAmount != null ? `${profile.incomeAmount}만원` : "-" },
      { label: "관심 분야", value: profile?.needs?.length ? profile.needs.join(", ") : "-" },
      { label: "특수 조건", value: profile?.specialConditions?.length ? profile.specialConditions.join(", ") : "-" },
    ],
    [age, profile]
  );

  const handleSend = async (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    setText("");
    await ensureSession();
    await sendMessage(trimmed);
  };

  const handleClickAvatarUpload = () => {
    avatarInputRef.current?.click();
  };

  const handleAvatarSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !profile) return;
    if (!file.type.startsWith("image/")) return;
    if (file.size > 5 * 1024 * 1024) {
      window.alert("프로필 사진은 5MB 이하 이미지만 업로드할 수 있습니다.");
      return;
    }

    const reader = new FileReader();
    reader.onload = async () => {
      const avatarUrl = typeof reader.result === "string" ? reader.result : "";
      if (!avatarUrl) return;
      saveLocalAvatarUrl(avatarUrl);
      await updateProfile({ ...profile, avatarUrl });
    };
    reader.readAsDataURL(file);
    event.target.value = "";
  };

  const handleAvatarRemove = async () => {
    if (!profile) return;
    clearLocalAvatarUrl();
    await updateProfile({ ...profile, avatarUrl: undefined });
  };


  return (
    <section className="grid grid-cols-1 gap-5 lg:grid-cols-[380px_1fr]">
      <div className="hidden lg:block space-y-2">
        {!isAuthenticated && <HeroBanner />}
        <article className="overflow-hidden rounded-lg border border-gray-300 bg-white">
          {isAuthenticated ? (
            <div className="flex h-full flex-col p-5">
              {showProfileInfo ? (
                <>
                  <h2 className="mt-1 mb-2 text-[18px] font-bold leading-none text-gray-900 px-2">정책 매칭 정보</h2>
                  <div className="mt-1 mb-2 rounded-xl bg-gray-50 px-4 py-2">
                    <p className="mt-1 text-xs text-gray-600">프로필 기반 추천 정보입니다. 정보가 정확할수록 추천 품질이 좋아집니다.</p>
                  </div>

                  <div className="flex-1 space-y-2">
                    {profileRows.map((row) => (
                      <div key={row.label} className="flex items-start justify-between gap-1 border-b border-gray-200 px-3 py-2">
                        <span className="text-sm text-gray-500">{row.label}</span>
                        <span className="max-w-[65%] text-right text-sm font-semibold text-gray-800">{row.value}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-2">
                    <Link href="/mypage/scraps" className="rounded-md border border-gray-300 bg-white px-2 py-2 text-center text-sm font-medium text-gray-700 hover:bg-gray-50">
                      북마크
                    </Link>
                    <Link href="/mypage" className="rounded-md border border-gray-300 bg-white px-2 py-2 text-center text-sm font-medium text-gray-700 hover:bg-gray-50">
                      마이페이지
                    </Link>
                    <button
                      type="button"
                      onClick={() => setShowProfileInfo(false)}
                      className="rounded-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      숨기기
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="mb-4 p-4">
                    <h2 className="text-[18px] font-bold leading-none text-gray-900">반갑습니다!</h2>
                  </div>

                  <div className="flex flex-1 flex-col items-center justify-center gap-2 pt-5 pb-8">
                    <div className="relative h-50 w-50 overflow-hidden rounded-full border-2 border-gray-200">
                      <Image
                        src={profile?.avatarUrl || "/mascot/profile-default.png"}
                        alt="프로필 사진"
                        fill
                        className="object-cover"
                      />
                    </div>
                    <p className="text-lg font-semibold text-gray-800 pb-1">
                      {profile?.displayName || "사용자"}님
                    </p>
                    <input
                      ref={avatarInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleAvatarSelected}
                    />

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleClickAvatarUpload}
                        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                      >
                        Upload
                      </button>
                      <button
                        type="button"
                        onClick={handleAvatarRemove}
                        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-2">
                    <Link href="/mypage/scraps" className="rounded-md border border-gray-300 bg-white px-2 py-2 text-center text-sm font-medium text-gray-700 hover:bg-gray-50">
                      북마크
                    </Link>
                    <Link href="/mypage" className="rounded-md border border-gray-300 bg-white px-2 py-2 text-center text-sm font-medium text-gray-700 hover:bg-gray-50">
                      마이페이지
                    </Link>
                    <button
                      type="button"
                      onClick={() => setShowProfileInfo(true)}
                      className="rounded-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      보이기
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="p-4">
              <LoginForm embedded />
            </div>
          )}
        </article>
      </div>

      <article className="flex h-[495px] flex-col overflow-hidden rounded-none border border-[#C7D5E1] bg-white">
        <div className="flex items-center justify-end px-3 pt-2">
          <button
            type="button"
            onClick={() => void refreshSession()}
            className="p-1 text-gray-500 transition hover:text-gray-800"
            aria-label="새로고침"
            title="새로고침"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 1 1-2.64-6.36M21 4v6h-6" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => void open()}
            className="ml-1 p-1 text-gray-500 transition hover:text-gray-800"
            aria-label="플로팅 열기"
            title="플로팅 열기"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="4" y="4" width="16" height="16" rx="2" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 14l6-6M12 8h4v4" />
            </svg>
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-7 pb-4 pt-2">
          {visibleMessages.length > 0 ? (
            visibleMessages.map((message, index) => (
              <div key={message.id}>
                <ChatMessageBubble message={message} />
                {/* 첫 번째 assistant 메시지(인사말) 뒤에 프로필 반영 버튼 */}
                {index === 0 && message.role === "assistant" && hasProfileData && (
                  <div className="ml-14 mt-2">
                    <button
                      type="button"
                      disabled={profileInjected || isLoading}
                      onClick={async () => {
                        setProfileInjected(true);
                        try {
                          await ensureSession();
                          await sendMessage("내 프로필 정보를 기반으로 맞춤 정책을 추천해주세요.", true);
                        } catch {
                          setProfileInjected(false);
                        }
                      }}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition cursor-pointer ${profileInjected
                        ? "border border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed"
                        : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 shadow-sm"
                        }`}
                    >
                      {profileInjected ? "✅ 내 정보가 반영되었습니다" : "내 정보 반영하기"}
                    </button>
                  </div>
                )}
              </div>
            ))
          ) : isLoading ? (
            <div className="flex items-start gap-3">
              <div className="mt-1 h-12 w-12 animate-pulse rounded-full bg-gray-200" />
              <div className="max-w-[78%] space-y-2 rounded-xl bg-[#DDE8F2] px-5 py-4">
                <div className="h-4 w-3/4 animate-pulse rounded bg-gray-300" />
                <div className="h-4 w-1/2 animate-pulse rounded bg-gray-300" />
              </div>
            </div>
          ) : null}

          {/* 메시지 전송 후 응답 대기 중 표시 */}
          {isLoading && visibleMessages.length > 0 && (
            <ThinkingIndicator />
          )}
        </div>

        <div className="border-t border-[#D3DCE5] px-6 pb-5 pt-4">
          <div className="mb-3 flex flex-wrap gap-2">

            {QUICK_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => void handleSend(tag)}
                className="rounded-md bg-[#DCE7F1] px-3 py-1 text-sm text-gray-800 hover:bg-[#cfddea]"
              >
                {tag}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <input
              className="h-14 min-w-0 flex-1 rounded-lg border border-[#C9D4DF] px-4 text-[15px] outline-none placeholder:text-gray-500"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="궁금하신 복지 혜택을 물어보세요..."
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                  void handleSend(text);
                }
              }}
            />
            <button
              type="button"
              onClick={() => void handleSend(text)}
              disabled={isLoading}
              className="flex h-14 w-16 items-center justify-center rounded-lg bg-[#6EA8D8] text-white transition hover:bg-[#5e99cc] disabled:cursor-not-allowed disabled:bg-gray-400"
              aria-label="전송"
            >
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12l14-7-4 7 4 7-14-7z" />
              </svg>
            </button>
          </div>
        </div>
      </article>
    </section>
  );
}
