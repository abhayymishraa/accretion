import { cn } from "@/lib/utils";
import type { ComponentProps } from "react";

// shadcn/ui Skeleton pattern (MIT), using Ember colors and optional motion.
// https://ui.shadcn.com/docs/components/skeleton
export function Skeleton({ className, ...props }: ComponentProps<"div">) {
    return (
        <div
            data-slot="skeleton"
            className={cn("rounded-[8px] bg-surface-2 motion-safe:animate-pulse", className)}
            {...props}
        />
    );
}
