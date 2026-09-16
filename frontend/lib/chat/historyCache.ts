import type { HistoryPage } from "@/types/chat.type";

// Memory only, session-scoped and bounded. Never reuse another account's history.
const pages = new Map<string, { page: HistoryPage; bytes: number }>();
let bytes = 0;
const MAX_BYTES = 2 * 1024 * 1024;

export function clearHistoryCache() {
    pages.clear();
    bytes = 0;
}

export function getHistoryCache(key: string) {
    return pages.get(key)?.page;
}

export function cacheHistory(key: string, page: HistoryPage) {
    const previous = pages.get(key);
    if (previous) bytes -= previous.bytes;
    pages.delete(key);
    const size = JSON.stringify(page).length * 2;
    if (size > MAX_BYTES) return;
    while (pages.size >= 8 || bytes + size > MAX_BYTES) {
        const [oldKey, old] = pages.entries().next().value!;
        pages.delete(oldKey);
        bytes -= old.bytes;
    }
    pages.set(key, { page, bytes: size });
    bytes += size;
}
