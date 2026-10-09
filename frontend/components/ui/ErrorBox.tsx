"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";

// Shared by auth, profile and chat. Lives here rather than in any feature because
// components/ui is this repo's home for controls more than one feature needs.
// `children` is an action offered with the error, such as Retry.
export function ErrorBox({
    message,
    children,
    className,
}: {
    message: string;
    children?: React.ReactNode;
    // A lighter look for an error that sits on a line of its own, such as under a list row.
    className?: string;
}) {
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
            className={cn(
                "rounded-[10px] border border-destructive/40 bg-destructive/8 px-4 py-3 text-[13px] leading-[1.5] wrap-anywhere text-destructive",
                className,
            )}
            role="alert"
            aria-live="polite"
        >
            {held}
            {children && <> {children}</>}
        </p>
    );
}
