"use client";

import { message } from "@/hooks/skills/useSkillLibrary";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";

/**
 * Finishes a connection sent back here. The code goes to the API from this signed-in page, so the
 * connection lands on the account that started it; the state is single-use, so it runs once.
 */
export function useConnectCallback<Account>({
    finish,
    accountKey,
    connected,
    back,
}: {
    finish: (code: string, state: string, params: URLSearchParams) => Promise<Account>;
    accountKey: string;
    connected: (account: Account) => string;
    back: string;
}) {
    const params = useSearchParams();
    const router = useRouter();
    const { mutate } = useSWRConfig();
    const [error, setError] = useState("");
    const started = useRef(false);
    const state = params.get("state");
    const code = params.get("code");
    const invalid =
        params.get("error") || !state || !code
            ? params.get("error") === "access_denied"
                ? "The connection was cancelled."
                : "The connection did not finish."
            : "";

    useEffect(() => {
        if (invalid || !state || !code || started.current) return;
        started.current = true;
        finish(code, state, params)
            .then(async (account) => {
                await mutate([accountKey], account, { revalidate: false });
                toast.success(connected(account));
                router.replace(back);
            })
            .catch((reason) => setError(message(reason, "The connection did not finish.")));
    }, [invalid, state, code, params, router, mutate, finish, accountKey, connected, back]);

    return { error: invalid || error };
}
