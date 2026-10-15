"use client";

import { message } from "@/hooks/skills/useSkillLibrary";
import { vercelService } from "@/services/service.vercel";
import type { Publish } from "@/types/vercel.type";
import { useState } from "react";
import useSWR from "swr";

// Vercel builds in the background; our API answers from its own row, so polling costs no call to Vercel.
const BUSY_POLL_MS = 3000;
export const publishBusy = (publish?: Publish | null) =>
    publish?.status === "uploading" || publish?.status === "building";

// Set before leaving for Vercel, read when the callback brings the user back: which project to return to,
// with its Publish sheet open again.
const RETURN_KEY = "accretion:publish:return";

function rememberReturn(projectId: string) {
    try {
        sessionStorage.setItem(RETURN_KEY, projectId);
    } catch {
        // Storage blocked (a private webview): the user lands on Projects instead.
    }
}

/** The project the user left from for Vercel, if any. */
export function returnProject(): string | null {
    try {
        return sessionStorage.getItem(RETURN_KEY);
    } catch {
        return null;
    }
}

/** Clears the return once the project the user came back to has opened its Publish sheet. */
export function takeReturn(projectId: string) {
    try {
        if (sessionStorage.getItem(RETURN_KEY) === projectId) sessionStorage.removeItem(RETURN_KEY);
    } catch {
        // Storage blocked: nothing was stored.
    }
}

/** The Publish sheet: the Vercel connection, this app's published copy, and the actions on it. */
export function usePublish(projectId: string, open: boolean) {
    const account = useSWR(open ? ["/vercel/account"] : null, () => vercelService.account());
    // A number, not a function of the data: SWR re-arms its timer only when this option changes, and the
    // React Compiler keeps an inline function's identity, so a function would never start polling again.
    const [busy, setBusy] = useState(false);
    const publish = useSWR(
        open ? (["/projects", projectId, "publish"] as const) : null,
        ([, id]) => vercelService.publish(id),
        {
            refreshInterval: busy ? BUSY_POLL_MS : 0,
            onSuccess: (data) => setBusy(publishBusy(data)),
        },
    );
    return {
        account: account.data ?? null,
        publish: publish.data ?? null,
        failed: Boolean(account.error || publish.error),
        retry: () => Promise.all([account.mutate(), publish.mutate()]),
        /** Each returns the error to show, or "". Connect leaves the page for Vercel. */
        connect: async () => {
            try {
                const url = await vercelService.beginConnect();
                rememberReturn(projectId);
                // Same tab: in-app browsers block new windows.
                window.location.assign(url);
                return "";
            } catch (reason) {
                return message(reason, "Could not start connecting Vercel.");
            }
        },
        start: async () => {
            try {
                const started = await vercelService.start(projectId);
                setBusy(publishBusy(started));
                await publish.mutate(started, { revalidate: false });
                return "";
            } catch (reason) {
                await account.mutate();
                return message(reason, "Could not start publishing.");
            }
        },
        unpublish: async () => {
            try {
                await vercelService.unpublish(projectId);
                await publish.mutate();
                return "";
            } catch (reason) {
                return message(reason, "Could not unpublish the app.");
            }
        },
    };
}
