// features/map/MapPageClient.tsx
"use client";

import { useState, useMemo } from "react";
import { KakaoMap } from "./components/KakaoMap";
import { MOCK_FACILITIES } from "./map.mock";
import { MapFacility, Location, MapFilterState } from "./map.types";

const APP_KEY_EXISTS = !!process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY;

export function MapPageClient() {
    // 상태 관리
    const [center, setCenter] = useState<Location>({ lat: 37.5665, lng: 126.9780 }); // 기본: 서울시청
    const [filter, setFilter] = useState<MapFilterState>({ category: "전체", search: "" });
    const [selectedFacility, setSelectedFacility] = useState<string | null>(null);

    // 카테고리 목록
    const categories = ["전체", "복지시설", "보육/교육시설", "공공기관", "의료기관", "편의시설"];

    // 필터링된 시설 목록
    const filteredFacilities = useMemo(() => {
        return MOCK_FACILITIES.filter((fac) => {
            const matchCategory = filter.category === "전체" || fac.category === filter.category;
            const matchSearch = filter.search === "" || fac.name.includes(filter.search) || fac.address.includes(filter.search);
            return matchCategory && matchSearch;
        });
    }, [filter]);

    // 시설 클릭 핸들러
    const handleFacilityClick = (fac: MapFacility) => {
        setSelectedFacility(fac.id);
        setCenter(fac.location); // 지도를 해당 시설로 이동
    };

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            <h1 className="mb-2 text-2xl font-bold">복지지도</h1>
            <p className="mb-6 text-sm text-gray-600">
                위치정보를 통해 다양한 복지시설을 찾을 수 있습니다.
            </p>

            {!APP_KEY_EXISTS && (
                <div className="mb-4 rounded-lg bg-yellow-50 p-4 text-sm text-yellow-800 border border-yellow-200">
                    ⚠️ <strong>Kakao Map API 키가 설정되지 않았습니다.</strong><br />
                    지도가 정상적으로 표시되지 않을 수 있습니다. `.env.local` 파일에 `NEXT_PUBLIC_KAKAO_MAP_API_KEY`를 설정해주세요.
                </div>
            )}

            <div className="grid gap-4 md:grid-cols-[360px_1fr] h-[calc(100vh-200px)] min-h-[600px]">
                {/* ✅ 왼쪽 패널: 필터 및 리스트 */}
                <section className="flex flex-col rounded-xl border bg-white p-4 h-full overflow-hidden">
                    {/* 상단 버튼들 */}
                    <div className="mb-3 grid grid-cols-2 gap-2 shrink-0">
                        <button
                            className="rounded-lg bg-gray-800 px-3 py-2 text-sm text-white hover:bg-gray-700 transition"
                            onClick={() => {
                                // 내 위치 찾기 (브라우저 API)
                                if (navigator.geolocation) {
                                    navigator.geolocation.getCurrentPosition(
                                        (pos) => setCenter({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
                                        (err) => alert("위치 정보를 가져올 수 없습니다.")
                                    );
                                } else {
                                    alert("이 브라우저는 위치 정보를 지원하지 않습니다.");
                                }
                            }}
                        >
                            내 위치 찾기
                        </button>
                        <button className="rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-800 hover:bg-gray-200 transition">
                            주소로 검색
                        </button>
                    </div>

                    {/* 카테고리 필터 */}
                    <div className="mb-3 flex flex-wrap gap-2 shrink-0">
                        {categories.map((cat) => (
                            <button
                                key={cat}
                                className={`rounded-full px-3 py-1 text-xs font-medium transition
                  ${filter.category === cat
                                        ? "bg-blue-600 text-white"
                                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                                    }`}
                                onClick={() => setFilter({ ...filter, category: cat })}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>

                    {/* 검색어 입력 */}
                    <div className="flex gap-2 mb-4 shrink-0">
                        <input
                            className="h-10 flex-1 rounded-lg border px-3 text-sm outline-none focus:border-blue-500"
                            placeholder="시설명 또는 주소 검색"
                            value={filter.search}
                            onChange={(e) => setFilter({ ...filter, search: e.target.value })}
                        />
                    </div>

                    <div className="mb-2 text-xs text-gray-500 shrink-0">
                        검색 결과 {filteredFacilities.length}건
                    </div>

                    {/* 리스트 영역 (스크롤) */}
                    <div className="flex-1 overflow-y-auto pr-1 space-y-3">
                        {filteredFacilities.map((fac) => (
                            <div
                                key={fac.id}
                                className={`rounded-lg border p-3 cursor-pointer transition
                  ${selectedFacility === fac.id
                                        ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                                        : "hover:border-gray-400"
                                    }`}
                                onClick={() => handleFacilityClick(fac)}
                            >
                                <div className="flex justify-between items-start">
                                    <div className="text-sm font-semibold text-gray-900">{fac.name}</div>
                                    <span className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                                        {fac.category}
                                    </span>
                                </div>
                                <div className="mt-1 text-xs text-gray-600">{fac.address}</div>
                                {fac.phone && <div className="mt-0.5 text-xs text-gray-500">📞 {fac.phone}</div>}
                            </div>
                        ))}

                        {filteredFacilities.length === 0 && (
                            <div className="py-10 text-center text-sm text-gray-400">
                                검색 결과가 없습니다.
                            </div>
                        )}
                    </div>
                </section>

                {/* ✅ 오른쪽 지도 영역 */}
                <section className="rounded-xl border bg-gray-50 overflow-hidden relative h-full">
                    <KakaoMap
                        center={center}
                        facilities={filteredFacilities}
                        selectedFacilityId={selectedFacility}
                        onMarkerClick={handleFacilityClick}
                    />
                </section>
            </div>
        </div>
    );
}
