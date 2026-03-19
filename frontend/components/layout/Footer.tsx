import Image from "next/image";
import Link from "next/link";

type FooterLink = {
  label: string;
  href: string;
  disabled?: boolean;
};

const FOOTER = {
  brand: {
    name: "복지나침반",
    tagline: "서울시민을 위한 맞춤형 복지 안내",
    logoSrc: "/logo/welfarecompass.png",
  },
  orgInfo: {
    orgName: "복지나침반 운영사무국(예시)",
    address: "(06373) 서울특별시 강남구 선릉로 35, 개포1동 주민센터 3·4층",
    tel: "02-0000-0000",
    email: "help@welfarecompass.kr",
    hours: "상담: 평일 09:00~18:00 (점심 12:00~13:00)",
  },
  links: [
    { label: "이용약관", href: "/terms" },
    { label: "개인정보처리방침", href: "/privacy" },
    { label: "오시는길", href: "/contact" },
    { label: "오픈 API 소개", href: "/open-api", disabled: true },
  ] satisfies FooterLink[],
};

export function Footer() {
  return (
    <footer className="mt-16 border-t bg-white">
      <div className="mx-auto grid max-w-[1280px] grid-cols-1 gap-10 px-4 py-8 md:grid-cols-12">
        <div className="md:col-span-4">
          <div className="flex items-center gap-3">
            <Image
              src={FOOTER.brand.logoSrc}
              alt={`${FOOTER.brand.name} 로고`}
              width={40}
              height={40}
              className="h-10 w-10 object-contain"
            />
            <div className="leading-tight">
              <p className="text-base font-semibold text-gray-900">{FOOTER.brand.name}</p>
              <p className="mt-1 text-xs text-gray-500">{FOOTER.brand.tagline}</p>
            </div>
          </div>

          <p className="mt-4 text-sm text-gray-600">
            조건을 입력하면 받을 수 있는 복지 프로그램을 추천해드립니다.
          </p>
        </div>

        <div className="md:col-span-8">
          <p className="text-sm font-semibold text-gray-900">{FOOTER.orgInfo.orgName}</p>

          <dl className="mt-3 space-y-2 text-sm text-gray-600">
            <div className="flex gap-2">
              <dt className="w-14 shrink-0 text-gray-500">주소</dt>
              <dd className="min-w-0 flex-1 break-keep">{FOOTER.orgInfo.address}</dd>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <div className="flex min-w-0 flex-1 gap-2">
                <dt className="w-14 shrink-0 text-gray-500">전화</dt>
                <dd>{FOOTER.orgInfo.tel}</dd>
              </div>

              <div className="flex min-w-0 flex-1 gap-2">
                <dt className="w-14 shrink-0 text-gray-500">Email</dt>
                <dd className="min-w-0 break-words">{FOOTER.orgInfo.email}</dd>
              </div>
            </div>

            <div className="flex gap-2">
              <dt className="w-14 shrink-0 text-gray-500">운영</dt>
              <dd>{FOOTER.orgInfo.hours}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="border-t bg-gray-50">
        <div className="mx-auto flex max-w-[1280px] flex-col gap-3 px-4 py-5 md:flex-row md:items-center md:justify-between">
          <nav className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            {FOOTER.links.map((l) =>
              l.disabled ? (
                <span key={l.href} aria-disabled="true" className="cursor-default text-gray-400">
                  {l.label}
                </span>
              ) : (
                <Link key={l.href} href={l.href} className="text-gray-700 hover:text-gray-900 hover:underline">
                  {l.label}
                </Link>
              ),
            )}
          </nav>

          <p className="text-xs text-gray-500">© {new Date().getFullYear()} WelfareCompass. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
