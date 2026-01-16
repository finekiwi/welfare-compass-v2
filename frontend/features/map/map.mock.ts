// features/map/map.mock.ts
import { MapFacility } from "./map.types";

// 서울시청 중심 목업 데이터
export const MOCK_FACILITIES: MapFacility[] = [
    {
        id: "1",
        name: "서울시청 복지센터",
        category: "복지시설",
        address: "서울특별시 중구 세종대로 110",
        phone: "02-120",
        location: { lat: 37.5665, lng: 126.9780 },
        description: "서울시민을 위한 종합 복지 센터입니다."
    },
    {
        id: "2",
        name: "중구 보건소",
        category: "의료기관",
        address: "서울특별시 중구 무교로 12",
        phone: "02-3396-4114",
        location: { lat: 37.5678, lng: 126.9790 },
        description: "지역 주민을 위한 보건 의료 서비스 제공"
    },
    {
        id: "3",
        name: "서울도서관",
        category: "보육/교육시설",
        address: "서울특별시 중구 세종대로 110",
        phone: "02-2133-0300",
        location: { lat: 37.5662, lng: 126.9784 },
        description: "시민 누구나 이용 가능한 시립 도서관"
    },
    {
        id: "4",
        name: "덕수궁",
        category: "편의시설",
        address: "서울특별시 중구 세종대로 99",
        phone: "02-771-9951",
        location: { lat: 37.5658, lng: 126.9751 },
        description: "휴식과 산책을 위한 문화유산"
    },
    {
        id: "5",
        name: "광화문우체국",
        category: "공공기관",
        address: "서울특별시 종로구 종로 6",
        phone: "02-732-0005",
        location: { lat: 37.5698, lng: 126.9781 },
    }
];
