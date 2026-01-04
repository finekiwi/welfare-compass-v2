// services/sse.ts

// ✅ SSE는 "연결을 열어두고 서버가 메시지를 푸시"하는 방식이라,
// fetch/axios가 아니라 EventSource를 씁니다.
// Django에서 StreamingHttpResponse + text/event-stream 형태로 맞춰주면 됩니다.
export function openSSE(url: string, onMessage: (data: string) => void) {
  const es = new EventSource(url);

  es.onmessage = (e) => {
    onMessage(e.data);
  };

  es.onerror = () => {
    // 연결 에러 시 닫아버리는 방식(단순)
    es.close();
  };

  return es; // 필요 시 외부에서 close() 가능
}
