// components/layout/Footer.tsx
import Link from "next/link";
import Image from "next/image";

/**
 * ✅ 기관형 Footer 레이아웃
 * - 좌측: 로고 + 서비스명(또는 기관명)
 * - 우측: 주소/연락처 + 운영시간 등 "텍스트 정보"
 * - 하단: 약관/개인정보/오시는길 + Copyright
 *
 * 실무적으로는:
 * - "푸터는 거의 안 바뀌는 정보"라서 하드코딩/환경변수/설정파일로 관리하는 경우가 많고
 * - 다국어(i18n)나 기관별 테마가 있으면 footerConfig.ts로 빼는 패턴이 흔함
 */

const FOOTER = {
  brand: {
    name: "복지나침반",
    tagline: "서울시민을 위한 맞춤형 복지 안내",
    // public/logo/welfarecompass.png 같은 경로로 교체
    logoSrc: "/logo/welfarecompass.png",
  },
  orgInfo: {
    // 임시데이터(나중에 실제 기관 정보로 교체)
    orgName: "복지나침반 운영사무국(임시)",
    address: "(04520) 서울특별시 중구 세종대로 124 (예시 주소)",
    tel: "02-0000-0000",
    email: "help@welfarecompass.example",
    hours: "상담: 평일 09:00~18:00 (점심 12:00~13:00)",
  },
  links: [
    { label: "이용약관", href: "/terms" },
    { label: "개인정보처리방침", href: "/privacy" },
    { label: "오시는길", href: "/contact" },
    { label: "오픈 API 소개", href: "/open-api" },
  ],
  // 선택: 인증마크/배너 영역 (원하면 삭제 가능)
  marks: [
    // public/marks/wa.png 같은 이미지 넣으면 스샷처럼 우측에 마크 배치 가능
    { alt: "웹 접근성 인증마크(예시)", src: "/marks/wa.png", w: 52, h: 52 },
  ],
};

export function Footer() {
  return (
    <footer className="mt-16 border-t bg-white">
      {/* 상단 영역: 로고/기관정보 */}
      <div className="mx-auto grid max-w-[1280px] grid-cols-1 gap-10 px-4 py-8 md:grid-cols-12">
        {/* 좌측: 브랜드 */}
        <div className="md:col-span-4">
          <div className="flex items-center gap-3">
            <Image
              src={FOOTER.brand.logoSrc}
              alt={`${FOOTER.brand.name} 로고`}
              width={40}
              height={40}
              className="h-10 w-10 object-contain"
              priority={false}
            />
            <div className="leading-tight">
              <p className="text-base font-semibold text-gray-900">
                {FOOTER.brand.name}
              </p>
              <p className="mt-1 text-xs text-gray-500">{FOOTER.brand.tagline}</p>
            </div>
          </div>

          {/* 필요하면 여기 한 줄 설명 추가 가능 */}
          <p className="mt-4 text-sm text-gray-600">
            조건을 입력하면 받을 수 있는 복지 프로그램을 추천해드려요.
          </p>
        </div>

        {/* 가운데: 기관 정보 */}
        <div className="md:col-span-6">
          <p className="text-sm font-semibold text-gray-900">{FOOTER.orgInfo.orgName}</p>

          <dl className="mt-3 space-y-2 text-sm text-gray-600">
            <div className="flex gap-2">
              <dt className="w-14 shrink-0 text-gray-500">주소</dt>
              <dd className="break-keep">{FOOTER.orgInfo.address}</dd>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <div className="flex gap-2">
                <dt className="w-14 shrink-0 text-gray-500">전화</dt>
                <dd>{FOOTER.orgInfo.tel}</dd>
              </div>

              <div className="flex gap-2">
                <dt className="w-14 shrink-0 text-gray-500">Email</dt>
                <dd className="break-all">{FOOTER.orgInfo.email}</dd>
              </div>
            </div>

            <div className="flex gap-2">
              <dt className="w-14 shrink-0 text-gray-500">운영</dt>
              <dd>{FOOTER.orgInfo.hours}</dd>
            </div>
          </dl>
        </div>

        {/* 우측: 마크/배너 */}
        <div className="md:col-span-2 md:flex md:justify-end">
          <div className="flex items-center gap-4 md:flex-col md:items-end">
            {/* 
            {FOOTER.marks.map((m) => (
              <Image
                key={m.src}
                src={m.src}
                alt={m.alt}
                width={m.w}
                height={m.h}
                className="h-auto w-auto object-contain"
              />
            ))} 
            */}
          </div>
        </div>
      </div>

      {/* 하단 영역: 약관/개인정보 링크 + 카피라이트 */}
      <div className="border-t bg-gray-50">
        <div className="mx-auto flex max-w-[1280px] flex-col gap-3 px-4 py-5 md:flex-row md:items-center md:justify-between">
          <nav className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            {FOOTER.links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-gray-700 hover:text-gray-900 hover:underline"
              >
                {l.label}
              </Link>
            ))}
          </nav>

          <p className="text-xs text-gray-500">
            © {new Date().getFullYear()} WelfareCompass. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
