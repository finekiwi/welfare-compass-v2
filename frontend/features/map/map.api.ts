import { api } from "@/services/axios";

export interface YouthCenter {
    cntrSn: string;
    cntrNm: string;
    cntrTelno: string;
    cntrAddr: string;
    cntrDaddr: string;
    cntrUrlAddr: string;
    stdgCtpvCd?: string;
    stdgSggCd?: string;
    lat?: number;  // 폴백 데이터에서 제공
    lng?: number;  // 폴백 데이터에서 제공
}

export interface FetchCentersResponse {
    page: number;
    page_size: number;
    results: YouthCenter[];
}

export async function fetchCenters(page = 1, pageSize = 100): Promise<YouthCenter[]> {
    try {
        const response = await api.get<FetchCentersResponse>("/api/policies/centers/", {
            params: { page, page_size: pageSize },
        });
        return response.data.results || [];
    } catch (error) {
        console.error("fetchCenters error:", error);
        return [];
    }
}

export interface MapPOI {
    id: number;
    theme: number;
    theme_name: string;
    name: string;
    latitude: number;
    longitude: number;
    address: string;
    phone: string;
    detail_url?: string;
    cot_conts_id: string;
    cot_theme_id: string;
    cot_theme_sub_id: string;
    theme_icon_url: string;
}

export async function fetchMapPOIs(themeId?: string): Promise<MapPOI[]> {
    try {
        const params = themeId ? { theme_id: themeId } : {};
        const response = await api.get<MapPOI[]>("/api/policies/map/pois/", { params });
        return response.data || [];
    } catch (error) {
        console.error("fetchMapPOIs error:", error);
        return [];
    }
}
