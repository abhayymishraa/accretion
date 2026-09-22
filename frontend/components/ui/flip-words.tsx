"use client";
// Flip Words from Aceternity UI. See ACETERNITY-LICENSE.
// https://ui.aceternity.com/components/flip-words
// Diverges from upstream: full transform strings so the motion runs on the
// compositor, a reduced-motion branch, a dissolve exit instead of a splash, and
// the cycle pauses while offscreen.
import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

export const FlipWords = ({
    words,
    duration = 3000,
    className,
}: {
    words: string[];
    duration?: number;
    className?: string;
}) => {
    const [currentWord, setCurrentWord] = useState(words[0]);
    const [isAnimating, setIsAnimating] = useState<boolean>(false);
    const reduced = useReducedMotion();
    // Stable across word swaps: the animated div is keyed and remounts, so the
    // observer has to sit on a wrapper that does not.
    const scope = useRef<HTMLSpanElement>(null);
    // Tracks "known to be offscreen", not "known to be onscreen", so the cycle
    // runs by default. If IntersectionObserver never reports — unsupported, or
    // starved as it is in headless Chrome — the behaviour is unchanged rather
    // than a permanently frozen headline.
    const [offscreen, setOffscreen] = useState(false);

    useEffect(() => {
        const el = scope.current;
        if (!el || typeof IntersectionObserver === "undefined") return;
        const io = new IntersectionObserver(([entry]) => setOffscreen(!entry.isIntersecting), {
            rootMargin: "200px",
        });
        io.observe(el);
        return () => io.disconnect();
    }, []);

    // thanks for the fix Julian - https://github.com/Julian-AT
    const startAnimation = useCallback(() => {
        const word = words[words.indexOf(currentWord) + 1] || words[0];
        setCurrentWord(word);
        setIsAnimating(true);
    }, [currentWord, words]);

    // Offscreen the cycle stops entirely: no word swap, no spring mount, no
    // main-thread work for something nobody can see. The upstream version also
    // never cleared its timeout.
    useEffect(() => {
        if (isAnimating || offscreen) return;
        const id = setTimeout(startAnimation, duration);
        return () => clearTimeout(id);
    }, [isAnimating, offscreen, duration, startAnimation]);

    return (
        <span ref={scope} className="inline-block">
            <AnimatePresence
                onExitComplete={() => {
                    setIsAnimating(false);
                }}
            >
                <motion.div
                    initial={{ opacity: 0, transform: "translateY(10px)" }}
                    animate={{ opacity: 1, transform: "translateY(0px)" }}
                    transition={
                        reduced
                            ? { duration: 0.15 }
                            : { type: "spring", duration: 0.5, bounce: 0.2 }
                    }
                    exit={
                        reduced
                            ? { opacity: 0, position: "absolute", transition: { duration: 0.12 } }
                            : {
                                  opacity: 0,
                                  transform: "translateY(-18px)",
                                  filter: "blur(6px)",
                                  position: "absolute",
                                  transition: { duration: 0.26, ease: [0.23, 1, 0.32, 1] },
                              }
                    }
                    className={cn("z-10 inline-block relative text-left px-2", className)}
                    key={currentWord}
                >
                    {/* edit suggested by Sajal: https://x.com/DewanganSajal */}
                    {currentWord.split(" ").map((word, wordIndex) => (
                        <motion.span
                            key={word + wordIndex}
                            initial={{
                                opacity: 0,
                                transform: "translateY(10px)",
                                filter: reduced ? "none" : "blur(6px)",
                            }}
                            animate={{
                                opacity: 1,
                                transform: "translateY(0px)",
                                filter: "blur(0px)",
                            }}
                            transition={{
                                delay: reduced ? 0 : wordIndex * 0.3,
                                duration: 0.3,
                            }}
                            className="inline-block whitespace-nowrap"
                        >
                            {word.split("").map((letter, letterIndex) => (
                                <motion.span
                                    key={word + letterIndex}
                                    initial={{
                                        opacity: 0,
                                        transform: "translateY(10px)",
                                        filter: reduced ? "none" : "blur(6px)",
                                    }}
                                    animate={{
                                        opacity: 1,
                                        transform: "translateY(0px)",
                                        filter: "blur(0px)",
                                    }}
                                    transition={{
                                        delay: reduced ? 0 : wordIndex * 0.3 + letterIndex * 0.05,
                                        duration: 0.2,
                                    }}
                                    className="inline-block"
                                >
                                    {letter}
                                </motion.span>
                            ))}
                            <span className="inline-block">&nbsp;</span>
                        </motion.span>
                    ))}
                </motion.div>
            </AnimatePresence>
        </span>
    );
};
