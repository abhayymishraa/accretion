"use client";

import { CallbackScreen } from "@/components/github/CallbackScreen";
import { useVercelCallback } from "@/hooks/publish/useVercelCallback";

/** Where Vercel returns after the user installs Accretion's Integration. */
export function VercelCallback() {
    const { error, back } = useVercelCallback();
    return (
        <CallbackScreen
            error={error}
            service="Vercel"
            back={back}
            backLabel={back === "/projects" ? "Back to projects" : "Back to your app"}
        />
    );
}
