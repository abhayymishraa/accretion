"use client";

import { ErrorBox } from "@/components/ui/ErrorBox";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useSkillDetail } from "@/hooks/skills/useSkillLibrary";
import type { SkillDraft } from "@/types/skill.type";
import { SHEET, SHEET_HEADER, SHEET_TITLE } from "./sheet";
import { SkillForm } from "./SkillForm";
import { TrustNotice } from "./TrustNotice";

interface SkillFormSheetProps {
    open: boolean;
    /** "new" to create; otherwise the id of the skill being edited. Kept while the panel closes. */
    target: string;
    /** Changes on every open, so a reopened form starts fresh. */
    formKey: number;
    onClose: () => void;
    save: (draft: SkillDraft, id?: string) => Promise<string>;
}

/** The side panel (full screen on a phone) that holds the add and edit form. */
export function SkillFormSheet({ open, target, formKey, onClose, save }: SkillFormSheetProps) {
    const editingId = target !== "new" ? target : null;
    const { skill, error } = useSkillDetail(editingId);
    const title = skill ? `Edit /${skill.name}` : editingId ? "Edit skill" : "New skill";

    return (
        <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
            <SheetContent className={`${SHEET} scroll-pb-16`}>
                <header className={SHEET_HEADER}>
                    <SheetTitle className={SHEET_TITLE}>{title}</SheetTitle>
                    <SheetDescription className="mt-1.5 text-[13.5px] leading-[1.55]">
                        Instructions Accretion follows whenever this skill fits the task.
                    </SheetDescription>
                </header>
                <TrustNotice />
                {editingId && !skill ? (
                    <div className="flex flex-col gap-6 px-5 py-6 sm:px-7">
                        {error ? (
                            <ErrorBox message={error} />
                        ) : (
                            <>
                                <Skeleton className="h-10 rounded-none" />
                                <Skeleton className="h-28 rounded-none" />
                                <Skeleton className="h-56 rounded-none" />
                            </>
                        )}
                    </div>
                ) : (
                    <SkillForm
                        key={`${target}-${formKey}`}
                        initial={skill}
                        onCancel={onClose}
                        onSubmit={async (draft) => {
                            const failure = await save(draft, editingId ?? undefined);
                            if (!failure) onClose();
                            return failure;
                        }}
                    />
                )}
            </SheetContent>
        </Sheet>
    );
}
