import { SupabaseCallback } from "@/components/supabase/SupabaseCallback";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Connecting Supabase · Accretion" };

// useSearchParams needs a Suspense boundary to render on the server.
export default function Page() {
    return (
        <Suspense>
            <SupabaseCallback />
        </Suspense>
    );
}
