"use client";

import React, { useEffect, useState, type ComponentPropsWithoutRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";

interface AnimatedListProps extends ComponentPropsWithoutRef<"div"> {
    children: React.ReactNode;
    delay: number;
}

export function AnimatedList({ children, className, delay, ...props }: AnimatedListProps) {
    const [index, setIndex] = useState(0);
    // Reduced motion shows the whole list at once instead of item by item.
    const reduce = useReducedMotion();
    const childrenArray = React.Children.toArray(children);

    useEffect(() => {
        if (index >= childrenArray.length - 1) return;
        const timeout = setTimeout(() => setIndex((prevIndex) => prevIndex + 1), delay);
        return () => clearTimeout(timeout);
    }, [index, delay, childrenArray.length]);

    // Kept in reading order (upstream reverses it, newest first): a checklist must not push the
    // rows already shown down as the next one arrives.
    const itemsToShow = childrenArray.slice(0, reduce ? childrenArray.length : index + 1);

    return (
        <div className={cn("flex flex-col items-center gap-4", className)} {...props}>
            <AnimatePresence>
                {itemsToShow.map((item) => (
                    <motion.div
                        key={(item as React.ReactElement).key}
                        // Never from nothing: a near-full scale reads as arriving, not growing out of a point.
                        initial={{ scale: 0.96, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1, originY: 0 }}
                        exit={{ scale: 0.96, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 350, damping: 40 }}
                        layout
                        className="mx-auto w-full"
                    >
                        {item}
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
}
