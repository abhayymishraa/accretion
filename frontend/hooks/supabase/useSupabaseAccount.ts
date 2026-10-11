"use client";

import { useRequireSession } from "@/hooks/auth/useHasSession";
import { message } from "@/hooks/skills/useSkillLibrary";
import { supabaseService } from "@/services/service.supabase";
import { toast } from "sonner";
import useSWR from "swr";

/** The Supabase page: the user's connection and the organizations it reaches. */
export function useSupabaseAccount() {
    const hasSession = useRequireSession();
    const account = useSWR(hasSession ? ["/supabase/account"] : null, () =>
        supabaseService.account(),
    );
    return {
        account: account.data ?? null,
        error: account.error
            ? message(account.error, "Could not load your Supabase connection.")
            : "",
        retry: () => account.mutate(),
        /** Sends the browser to Supabase in this tab: in-app browsers block new windows. */
        connect: async () => {
            try {
                window.location.assign(await supabaseService.beginConnect());
            } catch (reason) {
                toast.error(message(reason, "Could not open Supabase."));
            }
        },
        /** Returns the error to show, or "". */
        disconnect: async () => {
            try {
                await supabaseService.disconnect();
                await account.mutate();
                return "";
            } catch (reason) {
                return message(reason, "Could not disconnect Supabase.");
            }
        },
    };
}
