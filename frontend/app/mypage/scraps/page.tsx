import { ScrapList } from "@/features/mypage/ScrapList";

export default function MyScrapPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold text-gray-900">관심 정책</h1>
            <ScrapList />
        </div>
    );
}
