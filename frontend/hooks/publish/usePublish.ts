"use client";

import { message } from "@/hooks/skills/useSkillLibrary";
import { vercelService } from "@/services/service.vercel";
import type { Publish } from "@/types/vercel.type";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import useSWR from "swr";

// Vercel builds in the background; our API answers from its own row, so polling costs no call to Vercel.
const BUSY_POLL_MS = 3000;
export const publishBusy = (publish?: Publish | null) =>
    publish?.status === "uploading" || publish?.status === "building";
// The copy wants the user: a failure, a missing database, or changes not live yet.
export const publishNeedsYou = (publish?: Publish | null) =>
    publish?.status === "failed" ||
    publish?.status === "database" ||
    (publish?.status === "live" && !publish.current);

// Set before leaving for Vercel, read when the callback brings the user back: which project to return to,
// with its Publish tab open.
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

/** Clears the return once the project the user came back to has opened its Publish tab. */
export function takeReturn(projectId: string) {
    try {
        if (sessionStorage.getItem(RETURN_KEY) === projectId) sessionStorage.removeItem(RETURN_KEY);
    } catch {
        // Storage blocked: nothing was stored.
    }
}

/** This app's published copy alone. The tab, its panel, the phone's Workspace switch and the live toast share the
 * one request; a new saved revision refetches it, and the previous answer stays shown meanwhile. */
export function usePublishStatus(projectId: string, revisionId?: string | null) {
    // A number, not a function of the data: SWR re-arms its timer only when this option changes, and the
    // React Compiler keeps an inline function's identity, so a function would never start polling again.
    const [busy, setBusy] = useState(false);
    const publish = useSWR(
        ["/projects", projectId, "publish", revisionId ?? null] as const,
        ([, id]) => vercelService.publish(id),
        { refreshInterval: busy ? BUSY_POLL_MS : 0, keepPreviousData: true },
    );
    // Set from the shared data, not onSuccess: SWR calls onSuccess only in the hook that sent the request, so
    // the tab would keep polling after the panel saw the publish end, or never start.
    if (publishBusy(publish.data) !== busy) setBusy(!busy);
    return publish;
}

/** The panel says "You can leave this tab": a publish that goes live out of sight says so once. Called from the
 * workspace, which stays mounted when the panel, the tab row or the whole workspace is hidden. */
export function usePublishedToast(projectId: string, revisionId: string | null, watching: boolean) {
    const { data } = usePublishStatus(projectId, revisionId);
    const busy = publishBusy(data);
    const wasBusy = useRef(busy);
    useEffect(() => {
        if (wasBusy.current && !busy && data?.status === "live" && !watching)
            toast.success("Your app is live", {
                description: data.url?.replace(/^https?:\/\//, ""),
            });
        wasBusy.current = busy;
    }, [busy, data, watching]);
}

/** The Publish tab: the Vercel connection, this app's published copy, and the actions on it. */
export function usePublish(projectId: string, revisionId?: string | null) {
    const account = useSWR(["/vercel/account"], () => vercelService.account());
    const publish = usePublishStatus(projectId, revisionId);
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
        /** `land` applies the started publish to the screen, so the tab can animate the change it makes. */
        start: async (land: (update: () => void) => void) => {
            try {
                const started = await vercelService.start(projectId);
                land(() => void publish.mutate(started, { revalidate: false }));
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
