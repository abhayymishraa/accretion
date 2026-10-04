"use client";

import { useEffect, useRef } from "react";
import { useInView, useMotionValue, useSpring } from "motion/react";

// Trimmed to what this app uses: count up from 0 to a whole number once it is in view.
export function NumberTicker({ value }: { value: number }) {
    const ref = useRef<HTMLSpanElement>(null);
    const motionValue = useMotionValue(0);
    const springValue = useSpring(motionValue, { damping: 60, stiffness: 100 });
    const isInView = useInView(ref, { once: true });

    useEffect(() => {
        if (isInView) motionValue.set(value);
    }, [motionValue, isInView, value]);

    useEffect(
        () =>
            springValue.on("change", (latest) => {
                if (ref.current) {
                    ref.current.textContent = Intl.NumberFormat("en-US").format(Math.round(latest));
                }
            }),
        [springValue],
    );

    return (
        <span ref={ref} className="inline-block tracking-wider text-foreground tabular-nums">
            0
        </span>
    );
}
