"use client";

import HL from "@/components/mcp/hairline/kernel.js";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import { mount } from "./hairline/pegrail.js";

/**
 * A wall rail of empty pegs, drawn in the page's colours: the App keys tab with no keys yet. The peg under
 * the pointer slides out to take a key; it never plays on its own, and with reduced motion it reaches less.
 */
export function PegRail() {
    const stage = useRef<HTMLDivElement>(null);
    const reduce = useReducedMotion();
    // How far the slide reaches, in pegs.
    const reach = reduce ? 1 : 2;
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
    }, [reach]);
    return (
        <div
            ref={stage}
            data-hairline="pegrail"
            role="img"
            aria-label="An empty rail of pegs, waiting for keys."
            className="aspect-[5/4] [--hairline-plate:var(--background)] [--hairline-hi:var(--foreground)] [--hairline-edge:var(--muted-foreground)] [--hairline-mid:color-mix(in_oklab,var(--muted-foreground)_70%,var(--background))] [--hairline-lo:var(--border)] w-[150px]"
        />
    );
}
