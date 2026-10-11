import { GithubCallback } from "@/components/github/GithubCallback";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Connecting GitHub · Accretion" };

// useSearchParams needs a Suspense boundary to render on the server.
export default function Page() {
    return (
        <Suspense>
            <GithubCallback />
        </Suspense>
    );
}
