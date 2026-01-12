// features/map/MapPageClient.tsx
"use client";

export function MapPageClient() {
    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            <h1 className="mb-2 text-2xl font-bold">복지지도</h1>
            <p className="mb-6 text-sm text-gray-600">
                위치정보를 통해 다양한 복지시설을 찾을 수 있습니다. (지도 API는 추후 연결)
            </p>

            <div className="grid gap-4 md:grid-cols-[360px_1fr]">
                {/* 왼쪽 패널(필터/검색/결과리스트) 자리 */}
                <section className="rounded-xl border bg-white p-4">
                    <div className="mb-3 grid grid-cols-2 gap-2">
                        <button className="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white">
                            현위치
                        </button>
                        <button className="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white">
                            주소검색
                        </button>
                    </div>

                    <div className="mb-3 grid grid-cols-2 gap-2">
                        {["복지시설", "보육/교육시설", "공공기관", "의료기관", "편의시설"].map((t) => (
                            <button key={t} className="rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-700">
                                {t}
                            </button>
                        ))}
                    </div>

                    <select className="mb-2 h-10 w-full rounded-lg border px-3 text-sm">
                        <option>전체</option>
                    </select>

                    <div className="flex gap-2">
                        <input
                            className="h-10 flex-1 rounded-lg border px-3 text-sm"
                            placeholder="검색어를 입력하여 주세요."
                        />
                        <button className="h-10 rounded-lg bg-blue-600 px-4 text-sm text-white">
                            검색
                        </button>
                    </div>

                    <div className="mt-4 text-xs text-gray-500">검색 결과(목업)</div>

                    <div className="mt-3 space-y-3">
                        {[1, 2, 3].map((n) => (
                            <div key={n} className="rounded-lg border p-3">
                                <div className="text-sm font-semibold">시설명 {n}</div>
                                <div className="mt-1 text-xs text-gray-600">주소/전화/거리 등</div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* 오른쪽 지도 자리 */}
                <section className="rounded-xl border bg-gray-50">
                    <div className="flex h-[640px] items-center justify-center text-sm text-gray-500">
                        지도 영역 (API 연결 예정)
                    </div>
                </section>
            </div>
        </div>
    );
}
