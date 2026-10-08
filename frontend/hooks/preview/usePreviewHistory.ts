"use client";

import { useEffect, useRef, useState, type RefObject } from "react";

// Keeps the last 50 paths.
const LIMIT = 50;

/**
 * The preview's history, built from the page changes reported by the bridge that
 * agent/sandbox/preview_proxy.py adds to every page. Back and forward ask the bridge to load a
 * recorded path; a preview without the bridge reports nothing, and the buttons stay disabled.
 */
export function usePreviewHistory(
    frame: RefObject<HTMLIFrameElement | null>,
    appUrl: string | null,
) {
    const [history, setHistory] = useState({ entries: [] as string[], index: -1 });
    // The entry back/forward is moving to, so its report moves the cursor instead of adding a path.
    const stepping = useRef<number | null>(null);
    const origin = appUrl ? new URL(appUrl).origin : null;

    useEffect(() => {
        if (!origin) return;
        const onMessage = (event: MessageEvent) => {
            if (event.origin !== origin || event.source !== frame.current?.contentWindow) return;
            const { type, path } = (event.data ?? {}) as { type?: unknown; path?: unknown };
            if (type !== "accretion:location" || typeof path !== "string") return;
            if (!path.startsWith("/") || path.length > 2048) return;
            const target = stepping.current;
            stepping.current = null;
            setHistory(({ entries, index }) => {
                if (target !== null && entries[target] === path) return { entries, index: target };
                if (entries[index] === path) return { entries, index };
                const next = [...entries.slice(0, index + 1), path].slice(-LIMIT);
                return { entries: next, index: next.length - 1 };
            });
        };
        window.addEventListener("message", onMessage);
        return () => window.removeEventListener("message", onMessage);
    }, [frame, origin]);

    const send = (path: string) =>
        origin &&
        frame.current?.contentWindow?.postMessage({ type: "accretion:navigate", path }, origin);
    const go = (step: -1 | 0 | 1) => {
        const target = history.index + step;
        if (history.entries[target] === undefined) return;
        stepping.current = target;
        send(history.entries[target]);
    };

    return {
        path: history.entries[history.index] ?? null,
        /** Loads a typed path through the bridge; false when the preview has none to ask. */
        visit: (path: string) => {
            if (!origin || history.index < 0) return false;
            send(path);
            return true;
        },
        canBack: history.index > 0,
        canForward: history.index < history.entries.length - 1,
        back: () => go(-1),
        forward: () => go(1),
        // Reloads the page the app is on now, not the one the frame was first opened at.
        reload: () => go(0),
    };
}
