"use client";

import { useEffect, useState, type RefObject } from "react";

/**
 * The last error the preview's page reported through the bridge agent/sandbox/preview_proxy.py adds: an
 * uncaught error, a rejected promise or a build-error overlay. It clears when `resetKey` changes (a reload,
 * a build), so a fixed error does not stay on screen.
 */
export function usePreviewError(
    frame: RefObject<HTMLIFrameElement | null>,
    appUrl: string | null,
    resetKey: string,
) {
    const [error, setError] = useState<{ key: string; message: string } | null>(null);
    const origin = appUrl ? new URL(appUrl).origin : null;

    useEffect(() => {
        if (!origin) return;
        const onMessage = (event: MessageEvent) => {
            if (event.origin !== origin || event.source !== frame.current?.contentWindow) return;
            const data = (event.data ?? {}) as { type?: unknown; message?: unknown };
            const { type, message } = data;
            if (type !== "accretion:error" || typeof message !== "string" || !message.trim()) return;
            setError({ key: resetKey, message: message.slice(0, 2000) });
        };
        window.addEventListener("message", onMessage);
        return () => window.removeEventListener("message", onMessage);
    }, [frame, origin, resetKey]);

    return {
        message: error?.key === resetKey ? error.message : null,
        dismiss: () => setError(null),
    };
}
