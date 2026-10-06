"use client";

import { message } from "@/hooks/skills/useSkillLibrary";
import { connectionService } from "@/services/service.connections";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";

/**
 * Finishes a sign-in the service sent back here. The code goes to the API from this signed-in page, so the
 * sign-in lands on the account that started it; the state is single-use, so it runs once.
 */
export function useSignInCallback() {
    const params = useSearchParams();
    const router = useRouter();
    const { mutate } = useSWRConfig();
    const [error, setError] = useState("");
    const started = useRef(false);
    const state = params.get("state");
    const code = params.get("code");
    const denied = params.get("error");
    // A denied or abandoned sign-in leaves the server where it was; nothing to undo.
    const invalid =
        denied || !state || !code
            ? denied === "access_denied"
                ? "The sign-in was cancelled."
                : "The sign-in did not finish."
            : "";

    useEffect(() => {
        if (invalid || !state || !code || started.current) return;
        started.current = true;
        connectionService
            .finishSignIn(state, code, params.get("iss"))
            .then(async (server) => {
                await mutate(["/mcp-servers"]);
                toast.success(`${server.title} is connected. Review its tools.`);
                router.replace("/connectors");
            })
            .catch((reason) => setError(message(reason, "The sign-in did not finish.")));
    }, [invalid, state, code, params, router, mutate]);

    return { error: invalid || error };
}
