// features/map/components/KakaoMap.tsx
"use client";

import React, { useMemo, useState } from "react";
import { Map, MapMarker, CustomOverlayMap, useKakaoLoader } from "react-kakao-maps-sdk";
import { MapFacility, Location } from "../map.types";

interface KakaoMapProps {
    center: Location;
    myLocation?: Location | null;
    facilities: MapFacility[];
    selectedFacilityId: string | null;
    onMarkerClick: (facility: MapFacility) => void;
}

// 카테고리별 마커 색상 지정
const getCategoryColor = (category: string) => {
    if (category.includes("청년")) return "#3b82f6"; // blue
    if (category.includes("창업")) return "#10b981"; // green
    if (category.includes("마음") || category.includes("상담")) return "#f59e0b"; // amber
    if (category.includes("교육") || category.includes("도서관")) return "#8b5cf6"; // purple
    if (category.includes("어린이") || category.includes("돌봄")) return "#ec4899"; // pink
    if (category.includes("복지")) return "#06b6d4"; // cyan
    return "#ef4444"; // red (default)
};

// SVG 마커 생성기
const getMarkerImage = (color: string, isSelected: boolean) => {
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
}: KakaoMapProps) {
    // ✅ Kakao Map SDK 로드
    // 실제 키가 없으면 로드 실패하므로 에러 처리가 필요함
    const [loading, error] = useKakaoLoader({
        appkey: process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY || "YOUR_JAVASCRIPT_KEY", // 사용자 입력 필요
        libraries: ["services", "clusterer"],
    });

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
            level={3} // 확대 레벨
        >
            {/* 내 위치 마커 (있을 경우만 표시) */}
            {myLocation && (
                <MapMarker
                    position={myLocation}
                    title="내 위치"
                    image={{
                        src: getMarkerImage("#2563eb", true), // 돋보이는 파란색
                        size: { width: 30, height: 42 },
                    }}
                >
                    <div style={{ padding: "5px", color: "#2563eb", fontWeight: "bold", fontSize: "12px", textAlign: "center" }}>
                        현재 위치
                    </div>
                </MapMarker>
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

                const defaultSize = isCustomIconAvailable ? { width: 32, height: 32 } : { width: 24, height: 35 };
                const selectedSize = isCustomIconAvailable ? { width: 44, height: 44 } : { width: 30, height: 42 };

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
                                <div style={{
                                    padding: "12px", color: "#333", width: "200px",
                                    fontFamily: "sans-serif", backgroundColor: "white",
                                    border: "1px solid #ccc", borderRadius: "8px",
                                    boxShadow: "0 4px 6px rgba(0,0,0,0.1)"
                                }}>
                                    <div style={{ fontWeight: "bold", fontSize: "14px", marginBottom: "4px", lineHeight: "1.3" }}>
                                        {fac.name}
                                    </div>
                                    <div style={{ fontSize: "11px", color: "#3b82f6", fontWeight: "bold", marginBottom: "6px" }}>
                                        {fac.category}
                                    </div>
                                    {fac.address && <div style={{ fontSize: "12px", marginBottom: "4px", lineHeight: "1.3" }}>📍 {fac.address}</div>}
                                    {fac.phone && <div style={{ fontSize: "12px", marginBottom: "8px" }}>📞 {fac.phone}</div>}

                                    {(fac.url || fac.cot_conts_id) && (
                                        <div style={{ textAlign: "right", marginTop: "4px" }}>
                                            <a
                                                href={fac.url ? fac.url : `https://map.seoul.go.kr/smgis2/short/map/POI${fac.cot_conts_id}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{ fontSize: "12px", color: "#2563eb", textDecoration: "none", fontWeight: "bold", padding: "4px 8px", backgroundColor: "#eff6ff", borderRadius: "4px" }}
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
