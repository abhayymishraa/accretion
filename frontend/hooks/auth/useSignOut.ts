"use client";

import { clearSession } from "@/lib/auth/session";
import { useRouter } from "next/navigation";
import { useSWRConfig } from "swr";

/** Ends the session and drops every SWR cache entry, so the next account starts clean. */
export function useSignOut() {
    const router = useRouter();
    const { mutate } = useSWRConfig();
    return () => {
        clearSession();
        void mutate(() => true, undefined, { revalidate: false });
        router.push("/");
    };
}
