// features/home/HeroBanner.tsx
export function HeroBanner() {
  // ✅ ② 이미지의 큰 배너 영역
  // 나중에 public 이미지로 교체하면 됨: /public/hero.png 등
  return (
    <section className="mb-8 overflow-hidden rounded-2xl border bg-gray-50">
      <div className="flex min-h-[160px] items-center justify-center px-6 py-10 text-center">
        <div>
          <p className="text-lg font-semibold">
            서울시민을 위한 맞춤형 복지 안내
          </p>
          <p className="mt-2 text-sm text-gray-600">
            조건을 입력하면 받을 수 있는 복지 프로그램을 추천해드려요.
          </p>
        </div>
      </div>
    </section>
  );
}
