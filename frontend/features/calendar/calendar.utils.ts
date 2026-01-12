// features/calendar/calendar.utils.ts

/**
 * YYYYMMDD(예: "20251011") → Date
 */
export function parseYYYYMMDD(yyyymmdd: string): Date | null {
    const s = yyyymmdd?.trim();
    if (!s || s.length !== 8) return null;

    const y = Number(s.slice(0, 4));
    const m = Number(s.slice(4, 6));
    const d = Number(s.slice(6, 8));

    if (!y || !m || !d) return null;
    // JS Date: month는 0-based
    const dt = new Date(y, m - 1, d);
    // 유효성 체크(예: 20251399 같은 값 방지)
    if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return null;
    return dt;
}

/**
 * "20250916 ~ 20250926" → {start, end}
 * - 공백/물결 변형이 있어도 최대한 견고하게 처리
 */
export function parseAplyYmdRange(aplyYmd: string): { start: Date; end: Date } | null {
    if (!aplyYmd) return null;

    // 숫자 8자리(YYYYMMDD) 2개를 잡아내는 방식이 제일 안전
    const matches = aplyYmd.match(/\d{8}/g);
    if (!matches || matches.length < 2) return null;

    const start = parseYYYYMMDD(matches[0]);
    const end = parseYYYYMMDD(matches[1]);
    if (!start || !end) return null;

    return { start, end };
}

/**
 * 날짜를 "YYYY-MM-DD" 키로 변환(달력 셀 매핑용)
 */
export function toDateKey(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

/**
 * end 포함 범위에서 하루씩 증가시키며 DateKey 배열 생성
 * (이벤트가 여러 날짜에 걸칠 때 각 날짜 셀에 렌더링하기 위함)
 */
export function expandDateKeysInclusive(start: Date, end: Date): string[] {
    const keys: string[] = [];
    const cur = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    const last = new Date(end.getFullYear(), end.getMonth(), end.getDate());

    while (cur <= last) {
        keys.push(toDateKey(cur));
        cur.setDate(cur.getDate() + 1);
    }
    return keys;
}
