// features/map/components/KakaoMap.tsx
"use client";

import React, { useState, useEffect } from "react";
import { Map, MapMarker, CustomOverlayMap, useKakaoLoader, ZoomControl } from "react-kakao-maps-sdk";
import { MapFacility, Location } from "../map.types";

interface KakaoMapProps {
    center: Location;
    myLocation?: Location | null;
    facilities: MapFacility[];
    selectedFacilityId: string | null;
    onMarkerClick: (facility: MapFacility) => void;
    // For auto-adjustment
    filterCategory?: string;
}

// 카테고리별 마커 색상 지정
export const getCategoryColor = (category: string) => {
    if (category.includes("청년")) return "#3b82f6"; // blue
    if (category.includes("창업")) return "#10b981"; // green
    if (category.includes("마음") || category.includes("상담")) return "#f59e0b"; // amber
    if (category.includes("교육") || category.includes("도서관")) return "#8b5cf6"; // purple
    if (category.includes("어린이") || category.includes("돌봄")) return "#ec4899"; // pink
    if (category.includes("복지")) return "#06b6d4"; // cyan
    return "#ef4444"; // red (default)
};

// SVG 마커 생성기
export const getMarkerImage = (color: string, isSelected: boolean) => {
    const scale = isSelected ? 1.2 : 1;
    const dropShadow = isSelected ? `filter="drop-shadow(0px 4px 4px rgba(0,0,0,0.5))"` : "";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${24 * scale}" height="${35 * scale}" viewBox="0 0 24 35" ${dropShadow}>
        <path fill="${color}" stroke="#ffffff" stroke-width="1.5" d="M12 0C5.373 0 0 5.373 0 12c0 9 12 23 12 23s12-14 12-23C24 5.373 18.627 0 12 0zm0 17a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"/>
    </svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
};

export function KakaoMap({
    center,
    myLocation,
    facilities,
    selectedFacilityId,
    onMarkerClick,
    filterCategory,
}: KakaoMapProps) {
    // 내부 맵 객체 참조
    const [map, setMap] = useState<kakao.maps.Map | null>(null);

    // ✅ Kakao Map SDK 로드
    // 실제 키가 없으면 로드 실패하므로 에러 처리가 필요함
    const [loading, error] = useKakaoLoader({
        appkey: process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY || "YOUR_JAVASCRIPT_KEY", // 사용자 입력 필요
        libraries: ["services", "clusterer"],
    });

    // 카테고리나 시설 목록, 내 위치가 변경되었을 때 지도 범위 재조정
    useEffect(() => {
        if (!map || facilities.length === 0) return;

        let timerId: ReturnType<typeof setTimeout>;
        const bounds = new kakao.maps.LatLngBounds();

        if (myLocation && filterCategory) {
            // 1) "내 위치"가 있고, 검색 필터가 활성화된 경우 -> 내 위치 중심 반경 500m 정도가 보이도록 레벨 고정
            // 카카오맵 레벨 5 (250m 축척)가 대략 화면상 반경 500m를 한눈에 보기 좋습니다.
            map.setCenter(new kakao.maps.LatLng(myLocation.lat, myLocation.lng));

            // 모바일/PC 화면 크기에 따라 500m 반경이 딱 맞게 보이도록 레벨 5로 고정
            map.setLevel(5);
        } else {
            // 2) 전체 보기이거나, 내 위치가 없는 경우 -> 현재 필터링된 모든 마커가 보이도록 bounds 설정
            let pointsCount = 0;
            facilities.forEach(fac => {
                if (fac.location.lat !== 0 && fac.location.lng !== 0) {
                    bounds.extend(new kakao.maps.LatLng(fac.location.lat, fac.location.lng));
                    pointsCount++;
                }
            });

            // 내 위치도 있다면 포함
            if (myLocation) {
                bounds.extend(new kakao.maps.LatLng(myLocation.lat, myLocation.lng));
                pointsCount++;
            }

            // High: bounds가 비어 있는 빈 좌표 리스트일 때 오류가 발생하는 것을 방지
            if (pointsCount > 0) {
                map.setBounds(bounds);

                // map.setBounds()는 비동기적으로 동작할 수 있으므로, 약간의 지연 후 체크
                timerId = setTimeout(() => {
                    let targetLevel = map.getLevel();

                    // 사용자가 화면에 다 차게 보일 때 조금 더 타이트하게(확대해서) 보기를 원함
                    targetLevel -= 1;

                    if (targetLevel < 3) {
                        map.setLevel(3);
                    } else {
                        map.setLevel(targetLevel);
                    }
                }, 100);
            }
        }

        // Medium: 비동기 effect cleanup 불완전 해결
        return () => {
            if (timerId) clearTimeout(timerId);
        };
    }, [map, filterCategory, facilities, myLocation]);

    // 로딩 중이거나 에러 발생 시 (키 없음 등)
    if (loading) return <div className="flex h-full items-center justify-center bg-gray-100">지도 로딩 중...</div>;
    if (error) {
        return (
            <div className="flex h-full flex-col items-center justify-center bg-gray-100 p-6 text-center text-sm text-gray-500">
                <p className="mb-2 font-semibold text-red-500">지도를 불러올 수 없습니다.</p>
                <p>Kakao JavaScript 키가 필요합니다.</p>
                <p className="mt-2 text-xs text-gray-400">NEXT_PUBLIC_KAKAO_MAP_API_KEY 환경변수를 설정하세요.</p>
            </div>
        );
    }

    return (
        <Map
            center={center}
            style={{ width: "100%", height: "100%" }}
            level={4} // 기본 확대 레벨
            onCreate={setMap} // 지도 객체 생성 시 참조 획득
        >
            {/* 확대/축소 리모컨 */}
            <ZoomControl position={kakao.maps.ControlPosition.RIGHT} />

            {/* 내 위치 마커 (있을 경우만 표시) */}
            {myLocation && (
                <MapMarker
                    position={myLocation}
                    title="내 위치"
                    image={{
                        src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
                            `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="8" fill="#3b82f6" stroke="#ffffff" stroke-width="3" filter="drop-shadow(0px 2px 4px rgba(0,0,0,0.4))"/>
                            </svg>`
                        )}`,
                        size: { width: 24, height: 24 },
                    }}
                />
            )}

            {/* 시설 마커들 */}
            {facilities.map((fac) => {
                const isSelected = selectedFacilityId === fac.id;
                const markerColor = getCategoryColor(fac.category);
                // [BRAIN4-Map] 스마트서울맵 고유 마커 아이콘 우선 사용
                const isCustomIconAvailable = Boolean(fac.theme_icon_url);
                const markerSrc = isCustomIconAvailable
                    ? fac.theme_icon_url!
                    : getMarkerImage(markerColor, isSelected);

                // 커스텀 아이콘의 경우 자체 여백이 있을 수 있으므로 크기를 조금 더 크게 잡음
                const defaultSize = isCustomIconAvailable ? { width: 38, height: 38 } : { width: 24, height: 35 };
                const selectedSize = isCustomIconAvailable ? { width: 45, height: 45 } : { width: 30, height: 42 };

                return (
                    <React.Fragment key={fac.id}>
                        <MapMarker
                            position={fac.location}
                            clickable={true}
                            onClick={() => onMarkerClick(fac)}
                            image={{
                                src: markerSrc,
                                size: isSelected ? selectedSize : defaultSize,
                            }}
                            title={fac.name}
                            zIndex={isSelected ? 10 : 1}
                        />
                        {/* 마커 위에 커스텀 오버레이 표시 (선택되었을 때만) */}
                        {isSelected && (
                            <CustomOverlayMap position={fac.location} yAnchor={1.4} zIndex={15}>
                                {/* Low: 오버레이 인라인 스타일을 Tailwind 클래스로 추출하여 구조화 */}
                                <div className="p-4 w-[320px] max-w-[90vw] bg-white border border-gray-200 rounded-xl shadow-lg break-all whitespace-normal">
                                    <div className="font-bold text-[16px] mb-1.5 leading-snug text-gray-800">
                                        {fac.name}
                                    </div>
                                    <div className="text-[13px] text-blue-600 font-bold mb-2.5">
                                        {fac.category}
                                    </div>

                                    {fac.address && (
                                        <div className="flex items-start gap-1.5 text-[13px] mb-1.5 leading-snug text-gray-600">
                                            <svg className="shrink-0 mt-[1px]" width="14" height="14" viewBox="0 0 24 24" fill="#e11d48"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" /></svg>
                                            <span>{fac.address}</span>
                                        </div>
                                    )}
                                    {fac.phone && (
                                        <div className="flex items-center gap-1.5 text-[13px] mb-3 text-gray-600">
                                            <svg className="shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="#e11d48"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z" /></svg>
                                            <span>{fac.phone}</span>
                                        </div>
                                    )}

                                    {(fac.url || fac.cot_conts_id) && (
                                        <div className="text-right mt-2">
                                            <a
                                                href={fac.url ? fac.url : `https://map.kakao.com/link/search/${encodeURIComponent(fac.name)}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-block text-[13px] text-blue-700 font-bold py-1.5 px-3 bg-blue-50/80 rounded border border-blue-100 hover:bg-blue-100 transition-colors"
                                            >
                                                상세보기 &rarr;
                                            </a>
                                        </div>
                                    )}
                                </div>
                            </CustomOverlayMap>
                        )}
                    </React.Fragment>
                );
            })}
        </Map>
    );
}
