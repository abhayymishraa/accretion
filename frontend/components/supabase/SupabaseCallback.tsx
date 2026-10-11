"use client";

import { CallbackScreen } from "@/components/github/CallbackScreen";
import { useSupabaseCallback } from "@/hooks/supabase/useSupabaseCallback";

/** Where Supabase returns after the user signs in. */
export function SupabaseCallback() {
    const { error } = useSupabaseCallback();
    return <CallbackScreen error={error} service="Supabase" back="/integrations/supabase" />;
}
