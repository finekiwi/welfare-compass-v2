// features/map/map.types.ts

export interface Location {
    lat: number;
    lng: number;
}

export interface MapFacility {
    id: string;
    name: string;
    category: string;
    address: string;
    phone?: string;
    location: Location;
    description?: string;
    url?: string; // 상세 정보 URL (선택. 있는 경우 버튼 표시)
    cot_conts_id?: string; // 스마트서울맵 POI ID (상세정보 대체 링크)
    cot_theme_id?: string; // 스마트서울맵 테마 ID (마커 이미지에 사용)
    cot_theme_sub_id?: string; // 스마트서울맵 테마 서브 ID (마커 이미지에 사용)
    theme_icon_url?: string; // 스마트서울맵 테마 서브 ID (마커 이미지에 사용)
}

export interface MapFilterState {
    category: string | "전체";
    search: string;
    center?: Location;
}
