"use client";

import Image from "next/image";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { PolicyCardItem } from "./PolicyCard";
import type { ChatMessage } from "./chatbot.types";

function PolicyCarousel({ policies }: { policies: NonNullable<ChatMessage["policies"]> }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [cardsPerView, setCardsPerView] = useState(1);
  const [pageIndex, setPageIndex] = useState(0);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const updateCardsPerView = () => {
      const width = element.clientWidth;
      setCardsPerView(width >= 680 ? 2 : 1);
    };

    updateCardsPerView();
    const observer = new ResizeObserver(updateCardsPerView);
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  const totalPages = Math.max(1, Math.ceil(policies.length / cardsPerView));
  const safePageIndex = Math.min(pageIndex, totalPages - 1);

  const visiblePolicies = useMemo(() => {
    const start = safePageIndex * cardsPerView;
    return policies.slice(start, start + cardsPerView);
  }, [policies, safePageIndex, cardsPerView]);

  useEffect(() => {
    if (pageIndex > totalPages - 1) {
      setPageIndex(Math.max(0, totalPages - 1));
    }
  }, [pageIndex, totalPages]);

  return (
    <div ref={containerRef} className="w-full">
      <div className={`grid gap-2 ${cardsPerView === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
        {visiblePolicies.map((policy) => (
          <PolicyCardItem key={policy.plcy_no || policy.plcy_nm} policy={policy} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="mt-2 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => setPageIndex((prev) => Math.max(0, prev - 1))}
            disabled={safePageIndex === 0}
            className="h-7 w-7 rounded-full border border-gray-300 text-sm text-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="이전 정책"
          >
            ←
          </button>

          <span className="min-w-[52px] text-center text-xs text-gray-500">
            {safePageIndex + 1} / {totalPages}
          </span>

          <button
            type="button"
            onClick={() => setPageIndex((prev) => Math.min(totalPages - 1, prev + 1))}
            disabled={safePageIndex === totalPages - 1}
            className="h-7 w-7 rounded-full border border-gray-300 text-sm text-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="다음 정책"
          >
            →
          </button>
        </div>
      )}
    </div>
  );
}

export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const policies = message.policies ?? [];

  return (
    <div className={`flex ${isUser ? "justify-end" : "items-start gap-3"}`}>
      {!isUser && (
        <Image
          src="/mascot/chatbot.png"
          alt="챗봇 아이콘"
          width={50}
          height={50}
          className="h-11 w-11 shrink-0 p-1"
        />
      )}

      <div className={`flex flex-col gap-3 ${isUser ? "max-w-[80%] items-end" : "min-w-0 flex-1"}`}>
        <div
          className={[
            "rounded-2xl px-3 py-2 text-[15px] leading-relaxed",
            isUser ? "bg-blue-800 text-white" : "w-full bg-gray-100 text-gray-900",
          ].join(" ")}
        >
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-700 underline"
                  >
                    {children}
                  </a>
                ),
                p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="list-disc pl-4 mb-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-4 mb-1">{children}</ol>,
                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {!isUser && policies.length > 0 && (
          <div className="w-full">
            <PolicyCarousel policies={policies} />
          </div>
        )}
      </div>
    </div>
  );
}
