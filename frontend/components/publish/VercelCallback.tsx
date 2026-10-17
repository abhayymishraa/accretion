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
            to={back === "/projects" ? "projects" : "your app"}
        />
    );
}
