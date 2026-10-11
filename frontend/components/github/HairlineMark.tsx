"use client";

import HL from "@/components/mcp/hairline/kernel.js";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

type Mount = (
    parts: { stage: HTMLElement; svg: SVGSVGElement },
    reach: number,
) => { destroy: () => void };

/**
 * A service's mark built as a hairline figure, drawn in the page's colours: GitHub's coin over its slot,
 * Supabase's bolt in two halves. It answers the pointer and never plays on its own; with reduced motion
 * the pull reaches less, and the kernel lands every spring at once.
 */
export function HairlineMark({
    mount,
    label,
    className,
}: {
    mount: Mount;
    label: string;
    className: string;
}) {
    const stage = useRef<HTMLDivElement>(null);
    const reduce = useReducedMotion();
    // How far the pull reaches, in viewBox units.
    const reach = reduce ? 70 : 140;
    useEffect(() => {
        const el = stage.current;
        if (!el) return;
        HL.inject(document);
        const svg = HL.mk("svg", { viewBox: "0 0 400 320", "aria-hidden": "true" }, el);
        const drawn = mount({ stage: el, svg }, reach);
        return () => {
            drawn.destroy();
            svg.remove();
        };
    }, [mount, reach]);
    return (
        <div
            ref={stage}
            data-hairline="mark"
            role="img"
            aria-label={label}
            className={`aspect-[5/4] [--hairline-plate:var(--background)] [--hairline-hi:var(--foreground)] [--hairline-edge:var(--muted-foreground)] [--hairline-mid:color-mix(in_oklab,var(--muted-foreground)_70%,var(--background))] [--hairline-lo:var(--border)] ${className}`}
        />
    );
}
