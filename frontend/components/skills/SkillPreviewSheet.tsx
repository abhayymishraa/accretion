"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useSkillPreview } from "@/hooks/skills/useSkillLibrary";
import type { SkillSummary } from "@/types/skill.type";
import { Pencil } from "lucide-react";
import { Streamdown } from "streamdown";
import { SHEET, SHEET_HEADER } from "./sheet";
import styles from "./skills.module.css";

interface SkillPreviewSheetProps {
    open: boolean;
    /** Kept while the panel closes, so its content does not vanish mid-animation. */
    skill: SkillSummary | null;
    onClose: () => void;
    /** Library skills only: open the editor for this one. */
    onEdit: (id: string) => void;
}

/** A skill's full instructions, read-only: a side panel, full screen on a phone. */
export function SkillPreviewSheet({ open, skill, onClose, onEdit }: SkillPreviewSheetProps) {
    const { instructions, error } = useSkillPreview(open ? skill : null);
    const id = skill?.id;

    return (
        <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
            <SheetContent
                // Focus the panel, not its first control: opened from the keyboard, the browser would
                // ring that switch or button as if the user had tabbed to it. Tab still moves inside.
                onOpenAutoFocus={(event) => {
                    event.preventDefault();
                    (event.currentTarget as HTMLElement).focus();
                }}
                className={`${SHEET} outline-none`}
            >
                <header className={SHEET_HEADER}>
                    <SheetTitle className="min-w-0">
                        <code
                            className={`${styles.chip} inline-block max-w-full truncate px-2 py-1 font-mono text-[14px] leading-none`}
                        >
                            /{skill?.name}
                        </code>
                    </SheetTitle>
                    <SheetDescription className="mt-3 text-[13.5px] leading-[1.55]">
                        {skill?.description}
                    </SheetDescription>
                    <p className="mt-3 text-[12.5px] text-muted-foreground">
                        {skill?.source === "builtin" ? "Built in" : "Your skill"} · type /
                        {skill?.name} in chat to use it on purpose.
                    </p>
                </header>
                <div className="flex-1 px-5 py-5 sm:px-7">
                    {error ? (
                        <ErrorBox message={error} />
                    ) : instructions === null ? (
                        <div className="flex flex-col gap-3" aria-hidden="true">
                            <Skeleton className="h-4 w-2/3 rounded-none" />
                            <Skeleton className="h-3.5 w-full rounded-none" />
                            <Skeleton className="h-3.5 w-5/6 rounded-none" />
                            <Skeleton className="h-3.5 w-4/5 rounded-none" />
                        </div>
                    ) : (
                        <Streamdown
                            mode="static"
                            // Fades in where the skeleton was, instead of popping mid-slide.
                            linkSafety={{ enabled: false }}
                            className={`${styles.reveal} text-[13.5px] leading-[1.65] wrap-anywhere text-muted-foreground [&>*:first-child]:mt-0 [&_:is(h1,h2,h3,h4)]:mt-5 [&_:is(h1,h2,h3,h4)]:mb-1.5 [&_:is(h1,h2,h3,h4)]:text-[14.5px] [&_:is(h1,h2,h3,h4)]:font-semibold [&_:is(h1,h2,h3,h4)]:text-foreground [&_p]:my-2 [&_:is(ul,ol)]:my-2 [&_:is(ul,ol)]:pl-5 [&_li]:my-0.5 [&_strong]:text-foreground [&_a]:underline [&_:not(pre)>code]:bg-surface-3 [&_:not(pre)>code]:px-1 [&_:not(pre)>code]:font-mono [&_:not(pre)>code]:text-[0.9em]`}
                        >
                            {instructions}
                        </Streamdown>
                    )}
                </div>
                {id && (
                    <footer className="sticky bottom-0 border-t border-border bg-background">
                        <Button
                            variant="utility"
                            className="h-12 w-full rounded-none text-[13.5px]"
                            onClick={() => onEdit(id)}
                        >
                            <Pencil size={14} />
                            Edit this skill
                        </Button>
                    </footer>
                )}
            </SheetContent>
        </Sheet>
    );
}
