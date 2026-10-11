"use client";

import { useConnectCallback } from "@/hooks/integrations/useConnectCallback";
import { githubService } from "@/services/service.github";

/** Finishes a GitHub connection sent back here. */
export function useGithubCallback() {
    return useConnectCallback({
        finish: (code, state, params) =>
            githubService.finishConnect({
                code,
                state,
                installation_id: Number(params.get("installation_id")) || undefined,
            }),
        accountKey: "/github/account",
        connected: (account) => `GitHub is connected as ${account.login}.`,
        back: "/integrations/github",
    });
}
