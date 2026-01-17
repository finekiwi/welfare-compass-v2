"use client";

interface PaginationProps {
    currentPage: number;
    totalCount: number;
    itemsPerPage: number;
    onPageChange: (page: number) => void;
}

export function Pagination({
    currentPage,
    totalCount,
    itemsPerPage,
    onPageChange,
}: PaginationProps) {
    const totalPages = Math.ceil(totalCount / itemsPerPage);

    // 페이지가 1개 이하이면 숨김
    if (totalPages <= 1) return null;

    const pages = generatePageNumbers(currentPage, totalPages);

    return (
        <div className="flex items-center justify-center gap-2 py-8">
            <button
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="flex h-8 w-8 items-center justify-center text-gray-600 disabled:opacity-50 hover:text-black disabled:hover:bg-white"
                aria-label="이전 페이지"
            >
                &lt;
            </button>

            {pages.map((page, index) =>
                typeof page === "number" ? (
                    <button
                        key={index}
                        onClick={() => onPageChange(page)}
                        className={`flex h-8 w-8 items-center justify-center  ${currentPage === page
                            ? "text-gray-700 rounded border font-medium border-gray-700"
                            : "text-gray-700 font-medium hover:bg-gray-50 hover:rounded hover:border hover:border-gray-300"
                            }`}
                    >
                        {page}
                    </button>
                ) : (
                    <span key={index} className="px-1 text-gray-400">
                        ...
                    </span>
                )
            )}

            <button
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="flex h-8 w-8 items-center justify-center text-gray-600 disabled:opacity-50 hover:text-black disabled:hover:bg-white"
                aria-label="다음 페이지"
            >
                &gt;
            </button>
        </div>
    );
}

/**
 * 페이지 번호 생성 알고리즘 (예: 1 ... 4 5 6 ... 10)
 */
function generatePageNumbers(current: number, total: number): (number | string)[] {
    if (total <= 7) {
        return Array.from({ length: total }, (_, i) => i + 1);
    }

    const pages: (number | string)[] = [1];

    if (current > 4) {
        pages.push("...");
    }

    const start = Math.max(2, current - 2);
    const end = Math.min(total - 1, current + 2);

    for (let i = start; i <= end; i++) {
        pages.push(i);
    }

    if (current < total - 3) {
        pages.push("...");
    }

    pages.push(total);

    return pages;
}
