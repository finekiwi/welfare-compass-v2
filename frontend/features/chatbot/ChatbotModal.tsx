// features/chatbot/ChatbotModal.tsx
"use client";

import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useChatbotStore } from "@/stores/chatbot.store";
import { ChatWindow } from "./ChatWindow";

const VIEWPORT_GAP = 0;
const MIN_WIDTH = 340;
const MIN_HEIGHT = 420;

type DragState = {
  pointerOffsetX: number;
  pointerOffsetY: number;
};

type ResizeDirection =
  | "top"
  | "right"
  | "bottom"
  | "left"
  | "top-left"
  | "top-right"
  | "bottom-left"
  | "bottom-right";

type ResizeState = {
  direction: ResizeDirection;
  startX: number;
  startY: number;
  startWidth: number;
  startHeight: number;
  startLeft: number;
  startTop: number;
};

export function ChatbotModal() {
  const close = useChatbotStore((s) => s.close);
  const isLoading = useChatbotStore((s) => s.isLoading);
  const resetConversation = useChatbotStore((s) => s.resetConversation);
  const panelWidth = useChatbotStore((s) => s.panelWidth);
  const panelHeight = useChatbotStore((s) => s.panelHeight);
  const panelX = useChatbotStore((s) => s.panelX);
  const panelY = useChatbotStore((s) => s.panelY);
  const setPanelSize = useChatbotStore((s) => s.setPanelSize);
  const setPanelPosition = useChatbotStore((s) => s.setPanelPosition);
  const panelRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const resizeRef = useRef<ResizeState | null>(null);
  const restoreRectRef = useRef<{ width: number; height: number; x: number; y: number } | null>(null);
  const [isMaximized, setIsMaximized] = useState(false);

  const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

  const clampPosition = useCallback((x: number, y: number, width: number, height: number) => {
    const maxX = Math.max(VIEWPORT_GAP, window.innerWidth - width - VIEWPORT_GAP);
    const maxY = Math.max(VIEWPORT_GAP, window.innerHeight - height - VIEWPORT_GAP);
    return {
      x: clamp(x, VIEWPORT_GAP, maxX),
      y: clamp(y, VIEWPORT_GAP, maxY),
    };
  }, []);

  useEffect(() => {
    const handleResize = () => {
      const maxWidth = Math.max(MIN_WIDTH, window.innerWidth - VIEWPORT_GAP * 2);
      const maxHeight = Math.max(MIN_HEIGHT, window.innerHeight - VIEWPORT_GAP * 2);

      if (isMaximized) {
        if (panelWidth !== maxWidth || panelHeight !== maxHeight) {
          setPanelSize(maxWidth, maxHeight);
        }
        if (panelX !== VIEWPORT_GAP || panelY !== VIEWPORT_GAP) {
          setPanelPosition(VIEWPORT_GAP, VIEWPORT_GAP);
        }
        return;
      }

      const nextWidth = clamp(panelWidth, MIN_WIDTH, maxWidth);
      const nextHeight = clamp(panelHeight, MIN_HEIGHT, maxHeight);

      if (nextWidth !== panelWidth || nextHeight !== panelHeight) {
        setPanelSize(nextWidth, nextHeight);
      }

      if (panelX != null && panelY != null) {
        const nextPosition = clampPosition(panelX, panelY, nextWidth, nextHeight);
        if (nextPosition.x !== panelX || nextPosition.y !== panelY) {
          setPanelPosition(nextPosition.x, nextPosition.y);
        }
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [clampPosition, isMaximized, panelHeight, panelWidth, panelX, panelY, setPanelPosition, setPanelSize]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const panelEl = panelRef.current;
      if (!panelEl) return;

      if (dragRef.current) {
        const rect = panelEl.getBoundingClientRect();
        const nextPosition = clampPosition(
          event.clientX - dragRef.current.pointerOffsetX,
          event.clientY - dragRef.current.pointerOffsetY,
          rect.width,
          rect.height
        );
        setPanelPosition(nextPosition.x, nextPosition.y);
      }

      if (resizeRef.current) {
        const { direction, startX, startY, startWidth, startHeight, startLeft, startTop } = resizeRef.current;
        const deltaX = event.clientX - startX;
        const deltaY = event.clientY - startY;

        let nextLeft = startLeft;
        let nextTop = startTop;
        let nextWidth = startWidth;
        let nextHeight = startHeight;
        const startRight = startLeft + startWidth;
        const startBottom = startTop + startHeight;

        if (direction.includes("right")) {
          const maxWidthFromLeft = Math.max(MIN_WIDTH, window.innerWidth - startLeft - VIEWPORT_GAP);
          nextWidth = clamp(startWidth + deltaX, MIN_WIDTH, maxWidthFromLeft);
        }

        if (direction.includes("left")) {
          const leftLimit = clamp(
            startLeft + deltaX,
            VIEWPORT_GAP,
            startRight - MIN_WIDTH
          );
          nextLeft = leftLimit;
          nextWidth = startRight - leftLimit;
        }

        if (direction.includes("bottom")) {
          const maxHeightFromTop = Math.max(MIN_HEIGHT, window.innerHeight - startTop - VIEWPORT_GAP);
          nextHeight = clamp(startHeight + deltaY, MIN_HEIGHT, maxHeightFromTop);
        }

        if (direction.includes("top")) {
          const topLimit = clamp(
            startTop + deltaY,
            VIEWPORT_GAP,
            startBottom - MIN_HEIGHT
          );
          nextTop = topLimit;
          nextHeight = startBottom - topLimit;
        }

        setPanelPosition(nextLeft, nextTop);
        setPanelSize(nextWidth, nextHeight);
      }
    };

    const handlePointerUp = () => {
      dragRef.current = null;
      resizeRef.current = null;
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [clampPosition, setPanelPosition, setPanelSize]);

  const handleDragStart = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (isMaximized) return;
    if (event.button !== 0) return;
    const rect = panelRef.current?.getBoundingClientRect();
    if (!rect) return;

    dragRef.current = {
      pointerOffsetX: event.clientX - rect.left,
      pointerOffsetY: event.clientY - rect.top,
    };
    setPanelPosition(rect.left, rect.top);
  };

  const handleResizeStart =
    (direction: ResizeDirection) => (event: ReactPointerEvent<HTMLDivElement>) => {
      if (isMaximized) return;
      if (event.button !== 0) return;
      const rect = panelRef.current?.getBoundingClientRect();
      if (!rect) return;

      resizeRef.current = {
        direction,
        startX: event.clientX,
        startY: event.clientY,
        startWidth: rect.width,
        startHeight: rect.height,
        startLeft: rect.left,
        startTop: rect.top,
      };
      setPanelPosition(rect.left, rect.top);
    };

  const handleResetConversation = async () => {
    const confirmed = window.confirm("대화 내용을 초기화할까요?");
    if (!confirmed) return;
    await resetConversation();
  };

  const handleToggleMaximize = () => {
    const panelEl = panelRef.current;
    const maxWidth = Math.max(MIN_WIDTH, window.innerWidth - VIEWPORT_GAP * 2);
    const maxHeight = Math.max(MIN_HEIGHT, window.innerHeight - VIEWPORT_GAP * 2);

    if (isMaximized) {
      const restore = restoreRectRef.current;
      if (restore) {
        const nextPosition = clampPosition(restore.x, restore.y, restore.width, restore.height);
        setPanelSize(restore.width, restore.height);
        setPanelPosition(nextPosition.x, nextPosition.y);
      }
      setIsMaximized(false);
      return;
    }

    if (panelEl) {
      const rect = panelEl.getBoundingClientRect();
      restoreRectRef.current = {
        width: rect.width,
        height: rect.height,
        x: rect.left,
        y: rect.top,
      };
    } else {
      restoreRectRef.current = {
        width: panelWidth,
        height: panelHeight,
        x: panelX ?? window.innerWidth - panelWidth - VIEWPORT_GAP,
        y: panelY ?? window.innerHeight - panelHeight - VIEWPORT_GAP,
      };
    }

    setPanelSize(maxWidth, maxHeight);
    setPanelPosition(VIEWPORT_GAP, VIEWPORT_GAP);
    setIsMaximized(true);
  };

  return (
    <div
      ref={panelRef}
      className="fixed z-50 flex rounded-sm border bg-white shadow-2xl"
      style={{
        width: panelWidth,
        height: panelHeight,
        maxWidth: `calc(100vw - ${VIEWPORT_GAP * 2}px)`,
        maxHeight: `calc(100vh - ${VIEWPORT_GAP * 2}px)`,
        ...(panelX != null && panelY != null
          ? { left: panelX, top: panelY }
          : { right: VIEWPORT_GAP, bottom: VIEWPORT_GAP }),
      }}
    >
      <div className="flex h-full w-full flex-col overflow-hidden rounded-sm">
        <div
          className={`flex items-center justify-between border-b bg-slate-200 pl-4 pr-1 py-1 ${isMaximized ? "cursor-default" : "cursor-move"}`}
          onPointerDown={handleDragStart}
        >
          <div className="text-sm font-semibold">복지 상담 챗봇</div>
          <div className="flex items-center">
            <button
              type="button"
              onClick={handleResetConversation}
              disabled={isLoading}
              className="grid h-8 w-8 place-items-center text-gray-700 hover:text-gray-900 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="대화 초기화"
              title="대화 초기화"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5" />
              </svg>
            </button>
            <button
              type="button"
              onClick={handleToggleMaximize}
              className="grid h-8 w-8 place-items-center text-gray-700 hover:text-gray-900 cursor-pointer"
              aria-label={isMaximized ? "창 복원" : "최대화"}
              title={isMaximized ? "창 복원" : "최대화"}
            >
              {isMaximized ? (
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="7" y="7" width="10" height="10" rx="1" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="4" y="4" width="16" height="16" rx="1" />
                </svg>
              )}
            </button>
            <button
              type="button"
              onClick={close}
              className="grid h-8 w-8 place-items-center text-gray-700 hover:text-gray-900 cursor-pointer"
              aria-label="닫기"
              title="닫기"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1">
          <ChatWindow panelWidth={panelWidth} />
        </div>

        {!isMaximized && (
          <>
            <div
              aria-label="resize-top"
              onPointerDown={handleResizeStart("top")}
              className="absolute left-2 right-2 top-0 h-2 cursor-n-resize"
            />
            <div
              aria-label="resize-right"
              onPointerDown={handleResizeStart("right")}
              className="absolute bottom-2 right-0 top-2 w-2 cursor-e-resize"
            />
            <div
              aria-label="resize-bottom"
              onPointerDown={handleResizeStart("bottom")}
              className="absolute bottom-0 left-2 right-2 h-2 cursor-s-resize"
            />
            <div
              aria-label="resize-left"
              onPointerDown={handleResizeStart("left")}
              className="absolute bottom-2 left-0 top-2 w-2 cursor-w-resize"
            />
            <div
              aria-label="resize-top-left"
              onPointerDown={handleResizeStart("top-left")}
              className="absolute left-0 top-0 h-3 w-3 cursor-nw-resize"
            />
            <div
              aria-label="resize-top-right"
              onPointerDown={handleResizeStart("top-right")}
              className="absolute right-0 top-0 h-3 w-3 cursor-ne-resize"
            />
            <div
              aria-label="resize-bottom-left"
              onPointerDown={handleResizeStart("bottom-left")}
              className="absolute bottom-0 left-0 h-3 w-3 cursor-sw-resize"
            />
            <div
              aria-label="resize-bottom-right"
              onPointerDown={handleResizeStart("bottom-right")}
              className="absolute bottom-0 right-0 h-4 w-4 cursor-se-resize"
            />
          </>
        )}
      </div>
    </div>
  );
}
