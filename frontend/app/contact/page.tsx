"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Map, MapMarker, useKakaoLoader } from "react-kakao-maps-sdk";

const CAMPUS = {
  name: "청년취업사관학교 강남캠퍼스",
  address: "선릉로 35 개포1동주민센터 3, 4층 (지번 개포동 660-1)",
  // geocoding 실패 시 fallback 좌표
  lat: 37.4842,
  lng: 127.0584,
};

function IconBadge({
  bgClassName,
  children,
}: {
  bgClassName: string;
  children: ReactNode;
}) {
  return (
    <span className={`grid h-8 w-8 place-items-center rounded-full ${bgClassName}`}>
      {children}
    </span>
  );
}

function BusSvgIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 text-green-700" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="4" y="5" width="16" height="11" rx="2" />
      <path d="M4 10h16M8 16v3M16 16v3M7 19h2M15 19h2" />
    </svg>
  );
}

function SubwaySvgIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 text-green-700" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="6" y="3" width="12" height="14" rx="2" />
      <circle cx="10" cy="13" r="1" />
      <circle cx="14" cy="13" r="1" />
      <path d="M8 17l-2 3M16 17l2 3M9 7h6" />
    </svg>
  );
}

function ClockSvgIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 text-amber-700" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v5l3 2" />
    </svg>
  );
}

function ParkingSvgIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 text-blue-700" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M10 17V7h4a2.5 2.5 0 010 5h-4" />
    </svg>
  );
}

export default function ContactPage() {
  const [loading, error] = useKakaoLoader({
    appkey: process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY || "",
    libraries: ["services"],
  });

  const [center, setCenter] = useState({ lat: CAMPUS.lat, lng: CAMPUS.lng });

  useEffect(() => {
    if (loading || error) return;

    const kakaoAny = (window as any).kakao;
    if (!kakaoAny?.maps?.services?.Geocoder) return;

    const geocoder = new kakaoAny.maps.services.Geocoder();

    geocoder.addressSearch("서울 강남구 선릉로 35", (result: any[], status: string) => {
      if (status === kakaoAny.maps.services.Status.OK && result?.length) {
        setCenter({ lat: Number(result[0].y), lng: Number(result[0].x) });
        return;
      }

      geocoder.addressSearch("서울 강남구 개포동 660-1", (fallback: any[], fallbackStatus: string) => {
        if (fallbackStatus === kakaoAny.maps.services.Status.OK && fallback?.length) {
          setCenter({ lat: Number(fallback[0].y), lng: Number(fallback[0].x) });
        }
      });
    });
  }, [loading, error]);

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-4 text-2xl font-bold text-gray-900">오시는길</h1>
      <p className="mb-6 text-sm text-gray-700">{CAMPUS.address}</p>

      <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-5">
        <div className="h-[420px] overflow-hidden rounded-xl border border-gray-200 bg-gray-50 lg:col-span-3 lg:h-full">
          {loading && <div className="grid h-full place-items-center p-8 text-center text-sm text-gray-500">지도를 불러오는 중입니다.</div>}
          {error && (
            <div className="grid h-full place-items-center p-8 text-center text-sm text-red-500">
              카카오 지도를 불러오지 못했습니다. 지도 키 설정을 확인해주세요.
            </div>
          )}
          {!loading && !error && (
            <Map center={center} level={3} style={{ width: "100%", height: "100%" }}>
              <MapMarker position={center} title={CAMPUS.name} />
            </Map>
          )}
        </div>

        <aside className="rounded-xl border border-gray-200 bg-white p-5 lg:col-span-2">
          <section className="mb-6">
            <h2 className="mb-3 text-xl font-bold text-gray-900">교통수단</h2>
            <div className="space-y-4 text-gray-800">
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <IconBadge bgClassName="bg-green-100">
                    <BusSvgIcon />
                  </IconBadge>
                  <p className="text-lg font-semibold">버스</p>
                </div>
                <p className="text-sm leading-6">
                  3호선 도곡역 4번출구 → 버스 3414, 2413, 472, 4432, 3426, 강남10
                  <br />
                  (개포1동 주민센터, 개포고등학교 하차)
                </p>
              </div>
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <IconBadge bgClassName="bg-green-100">
                    <SubwaySvgIcon />
                  </IconBadge>
                  <p className="text-lg font-semibold">지하철</p>
                </div>
                <p className="text-sm leading-6">수인분당선 구룡역 5번출구 도보 10분</p>
              </div>
            </div>
          </section>

          <section className="mb-6 border-t pt-4">
            <div className="mb-2 flex items-center gap-2">
              <IconBadge bgClassName="bg-amber-100">
                <ClockSvgIcon />
              </IconBadge>
              <h2 className="text-lg font-bold text-gray-900">영업시간</h2>
            </div>
            <p className="mb-2 text-sm text-gray-700">운영 종료 08:00에 운영 시작(8시 0분에 운영 시작)</p>
            <ul className="space-y-1 text-sm text-gray-800">
              <li>월 08:00 - 21:00</li>
              <li>화 08:00 - 21:00</li>
              <li>수 08:00 - 21:00</li>
              <li>목 08:00 - 21:00</li>
              <li>금 08:00 - 21:00</li>
              <li>토 정기휴무 (매주 토요일)</li>
              <li>일 정기휴무 (매주 일요일)</li>
            </ul>
            <p className="mt-2 text-sm text-gray-700">- 22시부터 건물이 폐문됩니다</p>
          </section>

          <section className="border-t pt-4">
            <div className="mb-2 flex items-center gap-2">
              <IconBadge bgClassName="bg-blue-100">
                <ParkingSvgIcon />
              </IconBadge>
              <h2 className="text-lg font-bold text-gray-900">주차</h2>
            </div>
            <p className="text-sm text-gray-800">주차가능(무료)</p>
            <p className="text-sm text-gray-700">주차장은 지하 1층을 이용하시길 바랍니다.</p>
          </section>
        </aside>
      </div>
    </main>
  );
}
