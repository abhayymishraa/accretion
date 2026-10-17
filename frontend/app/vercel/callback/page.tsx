import { VercelCallback } from "@/components/publish/VercelCallback";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Connecting Vercel · Accretion" };

// useSearchParams needs a Suspense boundary to render on the server.
export default function Page() {
    return (
        <Suspense>
            <VercelCallback />
        </Suspense>
    );
}
