// features/map/components/KakaoMap.tsx
"use client";

import { useMemo, useState } from "react";
import { Map, MapMarker, useKakaoLoader } from "react-kakao-maps-sdk";
import { MapFacility, Location } from "../map.types";

interface KakaoMapProps {
    center: Location;
    facilities: MapFacility[];
    selectedFacilityId: string | null;
    onMarkerClick: (facility: MapFacility) => void;
}

export function KakaoMap({
    center,
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
            {/* 내 위치 (센터) 표시 - 선택사항 */}
            <MapMarker
                position={center}
                image={{
                    src: "/images/marker/my_location.png", // 없으면 기본 마커 사용됨 (아이콘 지정 안하면 됨)
                    size: { width: 24, height: 24 },
                }}
                title="현재 위치"
            />

            {/* 시설 마커들 */}
            {facilities.map((fac) => (
                <MapMarker
                    key={fac.id}
                    position={fac.location}
                    clickable={true}
                    onClick={() => onMarkerClick(fac)}
                    image={{
                        src: selectedFacilityId === fac.id
                            ? "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png" // 선택된 마커 (예시)
                            : "https://t1.daumcdn.net/mapjsapi/images/marker.png", // 기본 마커
                        size: selectedFacilityId === fac.id
                            ? { width: 24, height: 35 }
                            : { width: 24, height: 35 },
                    }}
                    title={fac.name}
                >
                    {/* 마커 위에 인포윈도우 표시 (선택되었을 때만) */}
                    {selectedFacilityId === fac.id && (
                        <div style={{ padding: "5px", color: "#000" }}>
                            {fac.name}
                        </div>
                    )}
                </MapMarker>
            ))}
        </Map>
    );
}
