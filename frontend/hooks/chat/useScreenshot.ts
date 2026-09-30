"use client";

import { useEffect, useState } from "react";

import { runService } from "@/services/service.runs";

/** An object URL for a stored screenshot, revoked when the image leaves the page. */
export function useScreenshot(runId: string, screenshotId: string) {
    const [url, setUrl] = useState<string | null>(null);
    const [failed, setFailed] = useState(false);
    useEffect(() => {
        const controller = new AbortController();
        let objectUrl: string | null = null;
        runService
            .screenshot(runId, screenshotId, controller.signal)
            .then((blob) => {
                objectUrl = URL.createObjectURL(blob);
                setUrl(objectUrl);
            })
            .catch(() => {
                if (!controller.signal.aborted) setFailed(true);
            });
        return () => {
            controller.abort();
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [runId, screenshotId]);
    return { url, failed };
}
