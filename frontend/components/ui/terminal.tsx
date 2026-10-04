"use client";

import { Children, createContext, useCallback, useContext, useEffect, useState } from "react";
import { motion } from "motion/react";

import { cn } from "@/lib/utils";

// Trimmed to what this app uses: one sequence, started at once, its lines appearing in order.
interface SequenceContextValue {
    completeItem: (index: number) => void;
    activeIndex: number;
}

// Every line sits inside a Terminal, which provides the real sequence.
const SequenceContext = createContext<SequenceContextValue>({
    completeItem: () => {},
    activeIndex: 0,
});
const ItemIndexContext = createContext(0);

/** This line's place in the sequence. Derived, not stored: the sequence only moves forward, so once
 * a line's turn has come it stays started. (Upstream latched it with setState in an effect, which
 * this repo's lint refuses.) */
function useTurn() {
    const { activeIndex, completeItem } = useContext(SequenceContext);
    const itemIndex = useContext(ItemIndexContext);
    return { started: activeIndex >= itemIndex, itemIndex, completeItem };
}

export const AnimatedSpan = ({
    children,
    className,
}: {
    children: React.ReactNode;
    className?: string;
}) => {
    const { started, itemIndex, completeItem } = useTurn();

    return (
        <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={started ? { opacity: 1, y: 0 } : { opacity: 0, y: -5 }}
            transition={{ duration: 0.3 }}
            className={cn("grid text-sm font-normal tracking-tight", className)}
            onAnimationComplete={() => completeItem(itemIndex)}
        >
            {children}
        </motion.div>
    );
};

export const TypingAnimation = ({
    children,
    className,
    duration,
}: {
    children: string;
    className?: string;
    duration: number;
}) => {
    const [displayedText, setDisplayedText] = useState("");
    const { started, itemIndex, completeItem } = useTurn();

    useEffect(() => {
        if (!started) return;
        let i = 0;
        const typing = setInterval(() => {
            if (i < children.length) {
                setDisplayedText(children.substring(0, i + 1));
                i++;
            } else {
                clearInterval(typing);
                completeItem(itemIndex);
            }
        }, duration);
        return () => clearInterval(typing);
    }, [children, duration, started, itemIndex, completeItem]);

    return (
        <span className={cn("text-sm font-normal tracking-tight", className)}>{displayedText}</span>
    );
};

export const Terminal = ({ children }: { children: React.ReactNode }) => {
    const [activeIndex, setActiveIndex] = useState(0);
    // Stable, so a typing line's interval does not restart when the next line begins.
    const completeItem = useCallback(
        (index: number) => setActiveIndex((current) => (index === current ? current + 1 : current)),
        [],
    );

    return (
        <SequenceContext.Provider value={{ completeItem, activeIndex }}>
            {/* One caller, the GitHub find log: its square, flat frame is written here once. */}
            <div className="z-0 h-full w-full border border-border bg-surface-1 font-mono">
                <div className="flex flex-col gap-y-2 border-b border-border p-4">
                    <div className="flex flex-row gap-x-2">
                        {/* Muted: the brand blue is the page's only accent colour. */}
                        {[0, 1, 2].map((dot) => (
                            <div key={dot} className="size-2 rounded-full bg-muted-foreground/40" />
                        ))}
                    </div>
                </div>
                <pre className="p-4 whitespace-pre-wrap [overflow-wrap:anywhere]">
                    <code className="grid gap-y-1 overflow-auto text-[12.5px]">
                        {Children.toArray(children).map((child, index) => (
                            <ItemIndexContext.Provider key={index} value={index}>
                                {child}
                            </ItemIndexContext.Provider>
                        ))}
                    </code>
                </pre>
            </div>
        </SequenceContext.Provider>
    );
};
