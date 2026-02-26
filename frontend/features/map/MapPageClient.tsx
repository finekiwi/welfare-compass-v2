// features/map/MapPageClient.tsx
"use client";

import { useState, useMemo, useEffect } from "react";
import { KakaoMap } from "./components/KakaoMap";
// import { MOCK_FACILITIES } from "./map.mock"; // Mock 제거
import { MapFacility, Location, MapFilterState } from "./map.types";
import { fetchCenters, fetchMapPOIs, YouthCenter } from "./map.api";

const APP_KEY_EXISTS = !!process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY;

export function MapPageClient() {
    // 상태 관리
    const [center, setCenter] = useState<Location>({ lat: 37.5665, lng: 126.9780 }); // 기본: 서울시청
    const [filter, setFilter] = useState<MapFilterState>({ category: "[동행]한 곳에 담은 청년공간", search: "" });
    const [selectedFacility, setSelectedFacility] = useState<string | null>(null);
    const [myLocation, setMyLocation] = useState<Location | null>(null);

    // 데이터 상태
    const [facilities, setFacilities] = useState<MapFacility[]>([]);
    const [loading, setLoading] = useState(false);

    // 동적 카테고리 목록 추출
    const categories = useMemo(() => {
        const uniqueCategories = new Set(facilities.map(fac => fac.category).filter(Boolean));
        return ["전체", "청년센터", ...Array.from(uniqueCategories).filter(c => c !== "청년센터")];
    }, [facilities]);

    // 데이터 로드
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

            setFacilities([...centerFacilities, ...poiFacilities]);
            setLoading(false);
        }).catch(err => {
            console.error("Failed to load map data", err);
            setLoading(false);
        });

        return () => { alive = false; };
    }, []);

    // 필터링된 시설 목록
    const filteredFacilities = useMemo(() => {
        return facilities.filter((fac) => {
            const matchCategory = filter.category === "전체" || fac.category === filter.category;
            const matchSearch = filter.search === "" || fac.name.includes(filter.search) || fac.address.includes(filter.search);
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
            // 좌표가 없는 경우 주소 검색으로 이동하는 로직이 필요할 수 있음 (KakaoMap 내부에서 처리 권장)
            // 여기서는 경고만
            console.log("좌표가 없습니다:", fac.name);
        }
    };

    return (
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8">
            <h1 className="mb-2 text-2xl font-bold">복지지도 (청년센터)</h1>
            <p className="mb-6 text-sm text-gray-600">
                전국의 청년센터 정보를 확인할 수 있습니다.
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
                                        (pos) => {
                                            const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                                            setCenter(loc);
                                            setMyLocation(loc);
                                        },
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
                                        ? "bg-blue-900 text-white"
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
                        {loading ? (
                            <div className="py-10 text-center text-sm text-gray-400">
                                데이터를 불러오는 중...
                            </div>
                        ) : (
                            <>
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
                            </>
                        )}
                    </div>
                </section>

                {/* ✅ 오른쪽 지도 영역 */}
                <section className="rounded-xl border bg-gray-50 overflow-hidden relative h-full">
                    <KakaoMap
                        center={center}
                        myLocation={myLocation}
                        facilities={filteredFacilities}
                        selectedFacilityId={selectedFacility}
                        onMarkerClick={handleFacilityClick}
                    />
                </section>
            </div>
        </div>
    );
}
