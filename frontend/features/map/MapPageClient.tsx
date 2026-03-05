// features/map/MapPageClient.tsx
"use client";

import { useState, useMemo, useEffect } from "react";
import { KakaoMap, getCategoryColor, getMarkerImage } from "./components/KakaoMap";
import { MapFacility, Location, MapFilterState } from "./map.types";
import { fetchCenters, fetchMapPOIs } from "./map.api";

const APP_KEY_EXISTS = !!process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY;

export function MapPageClient() {
    // 상태 관리
    const [center, setCenter] = useState<Location>({ lat: 37.5665, lng: 126.9780 }); // 기본: 서울시청
    const [filter, setFilter] = useState<MapFilterState>({ category: "전체", search: "" });
    const [selectedFacility, setSelectedFacility] = useState<string | null>(null);
    const [myLocation, setMyLocation] = useState<Location | null>(null);

    // ✅ 인라인 토스트 메시지 상태
    const [toastMsg, setToastMsg] = useState<string | null>(null);

    const showToast = (msg: string) => {
        setToastMsg(msg);
        setTimeout(() => setToastMsg(null), 3000);
    };

    // 데이터 상태
    const [facilities, setFacilities] = useState<MapFacility[]>([]);
    const [loading, setLoading] = useState(false);

    // 동적 카테고리 목록 추출
    const categories = useMemo(() => {
        const uniqueCategories = new Set(facilities.map(fac => fac.category).filter(Boolean));
        return ["전체", "청년센터", ...Array.from(uniqueCategories).filter(c => c !== "청년센터")];
    }, [facilities]);

    // 데이터 로드
    useEffect(() => {
        let alive = true;
        setLoading(true);

        Promise.all([
            fetchCenters(1, 1000),
            fetchMapPOIs() // 스마트서울맵 데이터
        ]).then(([centers, pois]) => {
            if (!alive) return;

            const centerFacilities: MapFacility[] = centers.map(c => ({
                id: `center-${c.cntrSn}`, // ID 충돌 방지
                name: c.cntrNm,
                category: "청년센터",
                location: {
                    lat: c.lat ?? 0,
                    lng: c.lng ?? 0,
                },
                address: c.cntrAddr + " " + (c.cntrDaddr || ""),
                phone: c.cntrTelno,
                url: c.cntrUrlAddr,
            }));

            const poiFacilities: MapFacility[] = pois.map(p => ({
                id: `poi-${p.id}`,
                name: p.name,
                category: p.theme_name || "기타", // 테마 이름을 카테고리로 사용
                location: {
                    lat: p.latitude,
                    lng: p.longitude,
                },
                address: p.address,
                phone: p.phone,
                url: p.detail_url,
                cot_conts_id: p.cot_conts_id,
                cot_theme_id: p.cot_theme_id,
                cot_theme_sub_id: p.cot_theme_sub_id,
                theme_icon_url: p.theme_icon_url,
                description: p.theme_name // 테마 이름을 설명으로 사용
            }));

            const allFacilities = [...centerFacilities, ...poiFacilities];
            // High: 좌표 없는 시설은 렌더링/bounds 계산에서 제외되도록 미리 필터링
            const validFacilities = allFacilities.filter(
                (f) => f.location.lat !== 0 && f.location.lng !== 0
            );

            setFacilities(validFacilities);
            setLoading(false);
        }).catch(err => {
            if (!alive) return;
            console.error("Failed to load map data", err); // Keep console.error for debugging, but add toast
            showToast("지도 데이터를 불러오는데 실패했습니다.");
            setLoading(false);
        });

        return () => { alive = false; };
    }, []);

    // 필터링된 시설 목록
    const filteredFacilities = useMemo(() => {
        return facilities.filter((fac) => {
            const matchCategory = filter.category === "전체" || fac.category === filter.category;
            const searchLower = filter.search.trim().toLowerCase();
            const matchSearch = filter.search === "" || fac.name.toLowerCase().includes(searchLower) || fac.address.toLowerCase().includes(searchLower);
            return matchCategory && matchSearch;
        });
    }, [filter, facilities]);

    // 시설 클릭 핸들러
    const handleFacilityClick = (fac: MapFacility) => {
        setSelectedFacility(fac.id);
        // 좌표가 유효한 경우만 이동
        if (fac.location.lat !== 0 && fac.location.lng !== 0) {
            setCenter(fac.location);
        } else {
            showToast("해당 시설은 좌표 정보가 제공되지 않습니다.");
        }
    };

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8 flex flex-col h-[calc(100vh-80px)] min-h-[800px]">

            {/* ✅ 상단 헤더 & 검색 바 */}
            <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-4 shrink-0">
                <div>
                    <h1 className="mb-2 text-3xl font-extrabold tracking-tight">복지지도(청년센터)</h1>
                    <p className="text-[15px] font-medium text-gray-700">
                        위치정보를 통해 다양한 복지시설을 찾으실 수 있습니다.
                    </p>
                </div>

                <div className="relative w-full md:w-[250px]">
                    <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none">
                        <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <input
                        className="h-8 w-full border-b-1 border-gray-300 pl-9 pr-4 text-[14px] outline-none focus:border-gray-400 transition "
                        placeholder="시설명 또는 주소 검색"
                        value={filter.search}
                        onChange={(e) => setFilter(prev => ({ ...prev, search: e.target.value }))}
                    />
                </div>
            </div>

            {!APP_KEY_EXISTS && (
                <div className="mb-4 rounded-lg bg-yellow-50 p-4 text-sm text-yellow-800 border border-yellow-200 shrink-0">
                    ⚠️ <strong>Kakao Map API 키가 설정되지 않았습니다.</strong><br />
                    지도가 정상적으로 표시되지 않을 수 있습니다. <code>.env.local</code> 파일에 <code>NEXT_PUBLIC_KAKAO_MAP_API_KEY</code>를 설정해주세요.
                </div>
            )}

            {/* ✅ 카테고리 필터 (마커 아이콘 포함) */}
            <div className="mb-6 flex flex-wrap gap-3 shrink-0">
                {categories.map((cat) => {
                    const repFac = facilities.find(f => f.category === cat);
                    const iconUrl = repFac?.theme_icon_url || getMarkerImage(getCategoryColor(cat), false);
                    const isSelected = filter.category === cat;

                    return (
                        <button
                            key={cat}
                            className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold transition-all
                                ${isSelected
                                    ? "border-blue-900 bg-white text-blue-900 ring-1 ring-blue-900"
                                    : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                                }`}
                            onClick={() => setFilter(prev => ({ ...prev, category: cat }))}
                        >
                            {cat !== "전체" && (
                                <div className="w-5 h-5 flex items-center justify-center shrink-0">
                                    <img src={iconUrl} alt="" className="max-w-full max-h-full object-contain drop-shadow-sm scale-110" />
                                </div>
                            )}
                            <span className="truncate">{cat}</span>
                        </button>
                    );
                })}
            </div>

            {/* ✅ 메인 하단 레이아웃 (리스트 + 지도) */}
            <div className="flex flex-col md:grid md:grid-cols-[380px_1fr] gap-4 md:h-[560px] flex-1 relative">

                {/* 토스트 메시지 오버레이 */}
                {toastMsg && (
                    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[200] bg-gray-800 text-white px-4 py-2 rounded-full shadow-lg text-sm font-medium animate-fade-in-down pointer-events-none">
                        {toastMsg}
                    </div>
                )}

                {/* 왼쪽 패널: 리스트 및 건수 / 내 위치 */}
                <section className="flex flex-col rounded-xl border-2 border-gray-200 bg-white overflow-hidden h-[400px] md:h-full shrink-0">
                    {/* 건수 및 내 위치 상단 헤더 */}
                    <div className="flex items-center justify-between px-4 py-3 border-b-2 border-gray-100 bg-gray-50 shrink-0">
                        <span className="text-[13px] text-gray-500 font-medium">
                            검색 결과 <span className="font-bold text-gray-900">{filteredFacilities.length}</span>건
                        </span>

                        <button
                            className="flex items-center gap-1.5 text-[14px] font-bold text-gray-800 hover:text-black transition cursor-pointer"
                            onClick={() => {
                                if (navigator.geolocation) {
                                    navigator.geolocation.getCurrentPosition(
                                        (pos) => {
                                            const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                                            setCenter(loc);
                                            setMyLocation(loc);
                                        },
                                        () => showToast("위치 정보를 가져올 수 없습니다.")
                                    );
                                } else {
                                    showToast("이 브라우저는 위치 정보를 지원하지 않습니다.");
                                }
                            }}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            내 위치 찾기
                        </button>
                    </div>

                    {/* 카드 리스트 */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50/30">
                        {loading ? (
                            <div className="py-20 flex flex-col items-center justify-center text-gray-400">
                                <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mb-3"></div>
                                <span className="text-sm font-medium">데이터를 불러오는 중...</span>
                            </div>
                        ) : (
                            <>
                                {filteredFacilities.map((fac) => (
                                    <div
                                        key={fac.id}
                                        className={`rounded-xl border p-4 cursor-pointer transition-colors
                                            ${selectedFacility === fac.id
                                                ? "border-blue-900 bg-blue-50/40 ring-1 ring-blue-900"
                                                : "border-gray-300 bg-white hover:border-gray-400"
                                            }`}
                                        onClick={() => handleFacilityClick(fac)}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <h3 className="text-[15px] font-bold text-gray-900 leading-tight pr-2">{fac.name}</h3>
                                            <span className="text-[10px] text-gray-500 bg-gray-100 flex-shrink-0 px-1.5 py-0.5 rounded font-medium border border-gray-200">
                                                {fac.category}
                                            </span>
                                        </div>
                                        <div className="text-[13px] text-gray-500 mb-1.5 leading-snug">{fac.address}</div>
                                        {fac.phone && (
                                            <div className="text-[13px] text-gray-500 font-medium flex items-center gap-1.5">
                                                <svg className="w-3.5 h-3.5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>
                                                {fac.phone}
                                            </div>
                                        )}
                                    </div>
                                ))}

                                {filteredFacilities.length === 0 && (
                                    <div className="py-20 text-center text-sm font-medium text-gray-400">
                                        검색 결과가 없습니다.
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </section>

                {/* 오른쪽 지도 영역 */}
                <section className="rounded-xl border-2 border-gray-200 bg-gray-100 overflow-hidden relative h-[400px] md:h-full shrink-0">
                    <KakaoMap
                        center={center}
                        myLocation={myLocation}
                        facilities={filteredFacilities}
                        selectedFacilityId={selectedFacility}
                        onMarkerClick={handleFacilityClick}
                        filterCategory={filter.category}
                    />
                </section>
            </div>
        </div>
    );
}
