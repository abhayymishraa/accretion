"use client";

import { useState } from "react";

// Shared by auth and profile. Lives here rather than in either feature because
// components/ui is this repo's home for controls more than one feature needs.
export function ErrorBox({ message }: { message: string }) {
    const [held, setHeld] = useState(message);
    if (message && message !== held) setHeld(message);

    // Nothing renders until there has actually been an error. Staying mounted
    // is only needed so a dismissal can animate out, and before the first error
    // there is nothing to dismiss. Relying on CSS to hide an empty box means a
    // stylesheet that has not loaded yet shows one.
    if (!held) return null;

    return (
        <p
            data-error-box={message ? "shown" : ""}
            className="rounded-[10px] border border-destructive/40 bg-destructive/8 px-4 py-3 text-[13px] leading-[1.5] text-destructive"
            role="alert"
            aria-live="polite"
        >
            {held}
        </p>
    );
}
