"use client";

import { useConnectCallback } from "@/hooks/integrations/useConnectCallback";
import { supabaseService } from "@/services/service.supabase";

/** Finishes a Supabase connection sent back here. */
export function useSupabaseCallback() {
    return useConnectCallback({
        finish: (code, state) => supabaseService.finishConnect(code, state),
        accountKey: "/supabase/account",
        connected: () => "Supabase is connected.",
        back: "/integrations/supabase",
    });
}
