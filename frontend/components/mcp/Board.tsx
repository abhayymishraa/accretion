"use client";

import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import { mount } from "./hairline/board.js";
import HL from "./hairline/kernel.js";
import type { ConnectorState } from "./ConnectorRow";

/**
 * A patch panel with one port per connector, drawn in the page's colours: live ones plugged in,
 * off ones pulled out, ones that need the user empty and lit. It answers the pointer and never
 * plays on its own; with reduced motion it answers less.
 */
export function Board({
    states,
    label,
    className,
}: {
    states: ConnectorState[];
    label: string;
    className: string;
}) {
    const stage = useRef<HTMLDivElement>(null);
    const reduce = useReducedMotion();
    // How far the lean reaches, in ports.
    const reach = reduce ? 1.45 : 3;
    const key = states.join();
    // The ports and which of them are empty: a change here redraws the board; live and off only move plugs.
    const shape = states.map((state) => (state === "attention" ? "a" : "p")).join("");
    const figure = useRef<ReturnType<typeof mount>>(null);
    const latest = useRef(key);
    useEffect(() => {
        latest.current = key;
        figure.current?.setStates(key.split(","));
    }, [key]);
    useEffect(() => {
        const el = stage.current;
        if (!el) return;
        HL.inject(document);
        const svg = HL.mk("svg", { viewBox: "0 0 400 320", "aria-hidden": "true" }, el);
        const drawn = mount({ stage: el, svg }, reach, latest.current.split(","));
        figure.current = drawn;
        return () => {
            drawn.destroy();
            svg.remove();
            figure.current = null;
        };
    }, [shape, reach]);
    return (
        <div
            ref={stage}
            data-hairline="board"
            role="img"
            aria-label={label}
            className={`aspect-[5/4] [--hairline-plate:var(--background)] [--hairline-hi:var(--foreground)] [--hairline-edge:var(--muted-foreground)] [--hairline-mid:color-mix(in_oklab,var(--muted-foreground)_70%,var(--background))] [--hairline-lo:var(--border)] ${className}`}
        />
    );
}
