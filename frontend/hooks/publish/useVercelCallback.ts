"use client";

import { useConnectCallback } from "@/hooks/integrations/useConnectCallback";
import { returnProject } from "@/hooks/publish/usePublish";
import { vercelService } from "@/services/service.vercel";
import { useState } from "react";

/** Finishes a Vercel connection sent back here, then returns to the project it started from, where the
 * Publish tab opens. */
export function useVercelCallback() {
    // Stored in this tab before it left for Vercel; the project page clears it.
    const [projectId] = useState(returnProject);
    const back = projectId ? `/chat/${encodeURIComponent(projectId)}` : "/projects";
    const result = useConnectCallback({
        finish: (code, state) => vercelService.finishConnect(code, state),
        accountKey: "/vercel/account",
        connected: () => "Vercel is connected.",
        back,
    });
    return { ...result, back };
}
