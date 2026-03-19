// features/home/HeroBanner.tsx
import Image from "next/image";

export function HeroBanner() {
  return (
    <section className="relative overflow-hidden">
      {/* ✅ 배경 이미지 */}
      <div className="relative h-[120px] w-full">
        <Image
          src="/hero2.png" // ✅ public/hero.png → src는 /hero.png
          alt="복지나침반 히어로 배너"
          fill
          className="object-cover scale-125 object-[center_60%]"
          priority
        />

        {/* ✅ 텍스트 가독성용 오버레이(반투명 레이어) */}
        <div className="absolute inset-0 bg-sky-100/50" />
      </div>

      {/* ✅ 텍스트 영역(이미지 위에 고정) */}
      <div className="absolute inset-0 flex items-center justify-center px-6 text-center">
        <div className="rounded-xl px-6 py-4">
          <p className="text-xl font-semibold text-gray-900">
            서울시민을 위한 맞춤형 복지 안내
          </p>
          <p className="mt-2 text-sm text-gray-700">
            조건을 입력하면 받을 수 있는 복지 프로그램을 추천해드려요.
          </p>
        </div>
      </div>
    </section>
  );
}
