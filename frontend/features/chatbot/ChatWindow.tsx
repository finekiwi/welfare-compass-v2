// features/chatbot/ChatWindow.tsx
"use client";

import { useEffect, useMemo, useRef } from "react";
import Link from "next/link";

import { useAuthStore } from "@/stores/auth.store";
import { useChatbotStore } from "@/stores/chatbot.store";
import { useProfileStore } from "@/stores/profile.store";
import { ChatInput } from "./ChatInput";
import { JOB_STATUS_LABELS, HOUSING_TYPE_LABELS } from "./chatbot.labels";
import { ChatMessageBubble } from "./ChatMessage";
import { ThinkingIndicator } from "./ThinkingIndicator";

const SIDEBAR_BREAKPOINT = 700;

export function ChatWindow({ panelWidth }: { panelWidth?: number }) {
  const messages = useChatbotStore((s) => s.messages);
  const isLoading = useChatbotStore((s) => s.isLoading);
  const hasProfileData = useChatbotStore((s) => s.hasProfileData);
  const sendMessage = useChatbotStore((s) => s.sendMessage);
  const ensureSession = useChatbotStore((s) => s.ensureSession);
  const profileInjected = useChatbotStore((s) => s.profileInjected);
  const setProfileInjected = useChatbotStore((s) => s.setProfileInjected);

  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const profile = useProfileStore((s) => s.profile);
  const fetchProfile = useProfileStore((s) => s.fetchProfile);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAuthenticated && !profile) {
      fetchProfile();
    }
  }, [isAuthenticated, profile, fetchProfile]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const showSidebar = useMemo(() => {
    if (!isAuthenticated) return false;
    if (panelWidth == null) return true;
    return panelWidth >= SIDEBAR_BREAKPOINT;
  }, [isAuthenticated, panelWidth]);

  const age = useMemo(() => {
    if (!profile?.birthYear) return null;
    return new Date().getFullYear() - profile.birthYear;
  }, [profile?.birthYear]);

  return (
    <div className={`grid h-full grid-cols-1 gap-4 p-5 ${showSidebar ? "grid-cols-[320px_1fr]" : ""}`}>
      {showSidebar && (
        <aside className="overflow-y-auto rounded-lg border bg-gray-50 p-4">
          <div className="text-sm font-semibold">내 정보 요약</div>
          <div className="mt-3 space-y-2 text-xs text-gray-700">
            <Row label="거주지" value={profile?.district || "-"} />
            <Row label="나이" value={age != null ? `만 ${age}세` : "-"} />
            <Row label="주거 형태" value={profile?.housingType ? HOUSING_TYPE_LABELS[profile.housingType] || "-" : "-"} />
            <Row label="취업 상태" value={profile?.jobStatus ? JOB_STATUS_LABELS[profile.jobStatus] || "-" : "-"} />
            <Row label="연 소득" value={profile?.incomeAmount != null ? `${profile.incomeAmount}만원` : "-"} />
            <Row label="관심 분야" value={profile?.needs?.length ? profile.needs.join(", ") : "-"} />
            <Row label="특수 조건" value={profile?.specialConditions?.length ? profile.specialConditions.join(", ") : "-"} />
          </div>

          <Link
            href="/mypage/profile"
            className="mt-4 block w-full rounded-xl border bg-white px-3 py-2 text-center text-xs transition hover:bg-gray-100"
          >
            내정보 업데이트
          </Link>
        </aside>
      )}

      <section className="flex h-full min-h-0 flex-col rounded-lg border">
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {messages.map((m, index) => (
            <div key={m.id}>
              <ChatMessageBubble message={m} />
              {index === 0 && m.role === "assistant" && hasProfileData && (
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
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                      profileInjected
                        ? "cursor-not-allowed border border-gray-200 bg-gray-100 text-gray-400"
                        : "cursor-pointer border border-gray-300 bg-white text-gray-700 shadow-sm hover:bg-gray-50"
                    }`}
                  >
                    {profileInjected ? "✅ 내 정보가 반영되었습니다" : "내 정보 반영하기"}
                  </button>
                </div>
              )}
            </div>
          ))}

          {isLoading && messages.length > 0 && <ThinkingIndicator />}
          <div ref={bottomRef} />
        </div>

        <div className="border-t p-3">
          <ChatInput />
        </div>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-white px-3 py-2">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
