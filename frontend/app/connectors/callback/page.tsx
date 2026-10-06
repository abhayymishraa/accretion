import { SignInCallback } from "@/components/mcp/SignInCallback";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Connecting · Accretion" };

// useSearchParams needs a Suspense boundary to render on the server.
export default function Page() {
    return (
        <Suspense>
            <SignInCallback />
        </Suspense>
    );
}
