"use client";

import { useReducedMotion } from "motion/react";
import Image from "next/image";
import { type CSSProperties, useEffect, useState } from "react";
import styles from "./skills.module.css";
import { slot } from "./SkillSections";

// Where each chip sits, in percent of the square. The connector runs from the
// core to (x, y); `side` says which edge of the chip that point touches, so a
// chip never hangs off the figure at phone width. Each pin cycles through the
// kinds of skill people teach, one pin at a time.
const PINS = [
    { labels: ["/brand-voice", "/tone-of-voice", "/no-jargon"], x: 18, y: 14, side: "left" },
    { labels: ["/pitch-deck", "/pricing-page", "/blog-layout"], x: 84, y: 22, side: "right" },
    { labels: ["/responsive-layout", "/mobile-first", "/dark-mode"], x: 10, y: 84, side: "left" },
    {
        labels: ["/accessibility-check", "/accessible-forms", "/seo-basics"],
        x: 92,
        y: 92,
        side: "right",
    },
] as const;
// Long enough to read a chip before the next one changes.
const CYCLE_MS = 2400;

const CORE = { x: 47, y: 50 };

/** The banner artwork: the Accretion orbit in halftone, with skills gathering around it. */
export function OrbitFigure() {
    const reduce = useReducedMotion();
    const [tick, setTick] = useState(0);
    useEffect(() => {
        // Reduced motion: the chips stay as they are.
        if (reduce) return;
        const timer = setInterval(() => setTick((current) => current + 1), CYCLE_MS);
        return () => clearInterval(timer);
    }, [reduce]);
    // Pin i moves on every fourth tick, offset so exactly one pin changes per tick.
    const label = (index: number) => {
        const labels = PINS[index].labels;
        return labels[Math.floor((tick + PINS.length - 1 - index) / PINS.length) % labels.length];
    };

    return (
        <div className="relative mx-auto aspect-square w-full max-w-[200px]" aria-hidden="true">
            <Image
                src="/skills/orbit-halftone.webp"
                alt=""
                width={720}
                height={720}
                priority
                className={`${styles.art} absolute inset-[12%] h-[76%] w-[76%] select-none`}
            />
            <svg viewBox="0 0 100 100" className="absolute inset-0 size-full overflow-visible">
                {PINS.map((pin, index) => (
                    <line
                        key={pin.x}
                        x1={CORE.x}
                        y1={CORE.y}
                        x2={pin.x}
                        y2={pin.y}
                        pathLength={1}
                        className={`${styles.line} stroke-foreground/35`}
                        strokeWidth={0.35}
                        vectorEffect="non-scaling-stroke"
                        style={slot(index)}
                    />
                ))}
                <rect
                    x={CORE.x - 1}
                    y={CORE.y - 1}
                    width={2}
                    height={2}
                    className="fill-foreground"
                />
            </svg>
            {PINS.map((pin, index) => (
                <span
                    key={pin.x}
                    className={`${styles.pin} absolute -translate-y-1/2 bg-background`}
                    style={
                        {
                            "--i": index,
                            top: `${pin.y}%`,
                            left: pin.side === "left" ? `${pin.x}%` : undefined,
                            right: pin.side === "right" ? `${100 - pin.x}%` : undefined,
                        } as CSSProperties
                    }
                >
                    {/* Keyed by its text, so each new label plays the swap-in once. */}
                    <span
                        key={label(index)}
                        className={`${styles.chip} ${styles.swap} block px-2 py-1 font-mono text-[11px] leading-none whitespace-nowrap`}
                    >
                        {label(index)}
                    </span>
                </span>
            ))}
        </div>
    );
}
