"use client";

// Adapted from shadcn/ui Sonner (MIT). See SHADCN-LICENSE.
// https://github.com/shadcn-ui/ui/blob/2b3e6d4f8d9161fe5c19340dc383aade392012dd/apps/v4/registry/new-york-v4/ui/sonner.tsx
import { CometSpinner } from "@/components/ui/comet-spinner";
import { CircleCheck, CircleX } from "lucide-react";
import type { CSSProperties } from "react";
import { Toaster as Sonner } from "sonner";

export function Toaster() {
    return (
        <Sonner
            position="bottom-right"
            closeButton
            visibleToasts={2}
            duration={4000}
            offset={24}
            mobileOffset={16}
            icons={{
                success: <CircleCheck size={17} />,
                error: <CircleX size={17} />,
                loading: <CometSpinner aria-hidden className="size-3.5" />,
            }}
            style={
                {
                    "--normal-bg": "var(--card)",
                    "--normal-text": "var(--foreground)",
                    "--normal-border": "var(--border)",
                    "--border-radius": "8px",
                } as CSSProperties
            }
            toastOptions={{ style: { fontFamily: "inherit" } }}
        />
    );
}
