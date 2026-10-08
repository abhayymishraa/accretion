"use client";

import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import { mount } from "./hairline/deck.js";
import HL from "@/components/mcp/hairline/kernel.js";

/**
 * A tray of browser-window cards, one per plan step, in Hairline's own strokes: built cards filed back, the rest
 * standing, the next one to build lit. It answers the pointer and never plays on its own.
 */
export function Deck({
    done,
    label,
    className,
}: {
    done: boolean[];
    label: string;
    className: string;
}) {
    const stage = useRef<HTMLDivElement>(null);
    const reduce = useReducedMotion();
    // The stagger between cards, in ms; reduced motion lands them together.
    const stagger = reduce ? 0 : 40;
    const key = done.map((built) => (built ? "1" : "0")).join("");
    useEffect(() => {
        const el = stage.current;
        if (!el) return;
        HL.inject(document);
        const svg = HL.mk("svg", { viewBox: "0 0 400 320", "aria-hidden": "true" }, el);
        const drawn = mount(
            { stage: el, svg },
            stagger,
            key.split("").map((c) => c === "1"),
        );
        return () => {
            drawn.destroy();
            svg.remove();
        };
    }, [key, stagger]);
    return (
        <div
            ref={stage}
            data-hairline="deck"
            role="img"
            aria-label={label}
            // Hairline's own strokes, as its pages draw them; only the fill takes the card's colour.
            className={`[--hairline-plate:var(--surface-2)] ${className}`}
        />
    );
}
