"use client";

import { Liquid } from "liquid-gooey";
import { Children, type ReactNode } from "react";

/** Buttons that bridge like liquid where they touch (liquid-gooey). Off: see config/effects.ts. */
export default function LiquidTools({ children }: { children: ReactNode }) {
    return (
        <Liquid
            blur={6}
            contrast={18}
            fill="var(--color-surface-3)"
            className="flex items-center gap-0.5"
        >
            {Children.map(children, (child) => (
                <Liquid.Item>{child}</Liquid.Item>
            ))}
        </Liquid>
    );
}
