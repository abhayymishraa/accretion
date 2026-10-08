"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

import { Deck } from "./Deck";
import { MessageContent } from "./MessageContent";

// A top-level checklist line of the plan: "- [ ] step" or "- [x] step".
const STEP = /^[-*] \[([ xX])\] /gm;
// Where the builder's part starts: the plan rules keep this heading as written, so the card can fold it.
const TECHNICAL = /^## How it will be built\s*$/m;

/** The plan's steps as a deck of browser cards, built ones filed back. Nothing when the plan has no checklist. */
export function PlanFigure({ plan }: { plan: string }) {
    const done = [...plan.matchAll(STEP)].map((step) => step[1] !== " ");
    if (!done.length) return null;
    return (
        <Deck
            done={done}
            label={`${done.filter(Boolean).length} of ${done.length} ${done.length === 1 ? "step" : "steps"} built`}
            className="mx-auto aspect-[5/4] h-44 max-w-full sm:h-52"
        />
    );
}

/** The plan as the user reads it: their part open, the builder's part folded. Its title is the card's heading. */
export function PlanText({ plan }: { plan: string }) {
    const [open, setOpen] = useState(false);
    const split = TECHNICAL.exec(plan);
    const product = split ? plan.slice(0, split.index) : plan;
    const technical = split ? plan.slice(split.index + split[0].length) : "";
    return (
        <div className="border-t border-hairline px-4 pb-4">
            <MessageContent content={product} className="[&_h1]:hidden" />
            {technical.trim() && (
                <>
                    <Button
                        variant="utility"
                        className="mt-2 min-h-11 px-0 text-[13px]"
                        aria-expanded={open}
                        onClick={() => setOpen(!open)}
                    >
                        {open ? "Hide technical details" : "Technical details"}
                    </Button>
                    <div data-disclosure={open ? "open" : ""}>
                        <MessageContent
                            content={technical}
                            className="text-[13.5px] text-muted-foreground [&_li:has(input)]:list-none [&_li:has(input)]:-ml-5 [&_input]:mr-2 [&_input]:size-3.5 [&_input]:translate-y-[2px] [&_input]:accent-foreground"
                        />
                    </div>
                </>
            )}
        </div>
    );
}
