import type { ReactNode } from "react";

// Shared by chat controls whose icon changes with their state (send -> spinner, copy -> check).
// Both icons share one grid cell and cross-fade, so the swap reads as a change rather than a cut.
// Grid items are blockified, which is what lets the inline icons take a scale transform.
export function IconSwap({
    swapped,
    from,
    to,
}: {
    swapped: boolean;
    from: ReactNode;
    to: ReactNode;
}) {
    return (
        <span className="grid place-items-center [&>*]:[grid-area:1/1] [&>*]:transition-[opacity,scale] [&>*]:duration-150 [&>*]:ease-[var(--ease-out)] motion-reduce:[&>*]:scale-100">
            <span className={swapped ? "scale-80 opacity-0" : undefined}>{from}</span>
            <span className={swapped ? undefined : "scale-80 opacity-0"}>{to}</span>
        </span>
    );
}
