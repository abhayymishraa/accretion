import { FileIcon } from "@/components/files/FileIcon";
import { ICON_ROOM, mentionTargets, splitMentions } from "@/hooks/chat/useComposerMenu";
import type { ProjectSkill } from "@/types/skill.type";
import { ScrollText } from "lucide-react";

// A pill's colours. Its shadows widen it into the spaces around it; a folder's pill has no right one.
const MARK =
    "rounded-[5px] bg-primary/15 text-[color-mix(in_oklab,var(--primary)_78%,var(--foreground))]";
const SKILL_MARK = `${MARK} [box-shadow:-0.15em_0_0_0_color-mix(in_oklab,var(--primary)_15%,transparent),0.12em_0_0_0_color-mix(in_oklab,var(--primary)_15%,transparent)]`;
const FOLDER_MARK = `${MARK} [box-shadow:-0.15em_0_0_0_color-mix(in_oklab,var(--primary)_15%,transparent)]`;

/**
 * The composer's mirror layer: the prompt as you see it, with "@" mentions of project files and
 * folders and "/" picks of enabled skills in the brand blue. It sits under a transparent textarea
 * that keeps the caret, so it must render every character at the textarea's exact width.
 */
export function PromptMirror({
    text,
    files,
    skills,
}: {
    text: string;
    files: string[];
    skills: ProjectSkill[] | null;
}) {
    const skillNames = new Set((skills ?? []).filter((skill) => skill.enabled).map((s) => s.name));
    const parts = splitMentions(text, new Set(mentionTargets(files)), skillNames);
    // A pick from the menu ends the text before it with ICON_ROOM; its pill draws over that room.
    const picked = (index: number) => {
        const before = parts[index - 1];
        const part = parts[index];
        return typeof part === "object" && "skill" in part && typeof before === "string"
            ? before.endsWith(ICON_ROOM)
            : false;
    };
    return (
        <>
            {parts.map((part, index) =>
                typeof part === "string" ? (
                    picked(index + 1) ? (
                        part.slice(0, -1)
                    ) : (
                        part
                    )
                ) : "skill" in part ? (
                    picked(index) ? (
                        <mark key={index} className="relative bg-transparent">
                            {/* The room, "/" and name keep their widths, hidden; the pill is
                                drawn over them, sized to its own smaller, bolder text, so its
                                padding is even on both sides. */}
                            <span className="invisible">
                                {ICON_ROOM}/{part.skill}
                            </span>
                            <span className="absolute inset-y-0 left-0 flex items-center gap-[0.22em] rounded-[3px] bg-primary/15 px-1.5 whitespace-nowrap text-[color-mix(in_oklab,var(--primary)_78%,var(--foreground))]">
                                <ScrollText aria-hidden="true" className="size-[0.85em]" />
                                <span className="text-[0.92em] font-medium text-foreground">
                                    {part.skill}
                                </span>
                            </span>
                        </mark>
                    ) : (
                        <mark key={index} className={SKILL_MARK}>
                            /{part.skill}
                        </mark>
                    )
                ) : (
                    <mark
                        key={index}
                        className={part.path.endsWith("/") ? FOLDER_MARK : SKILL_MARK}
                    >
                        {/* Visual only: the mirror must keep the textarea's exact
                            widths or the caret drifts. Shadows widen the pill into the
                            spaces around it, the icon sits left in the "@" slot with a
                            gap before the name, and a folder's "/" is hidden but sent. */}
                        <span className="relative">
                            <span className="invisible">@</span>
                            <span className="absolute inset-y-0 left-[-0.05em] flex items-center [&_img]:size-[0.68em]">
                                <FileIcon filename={part.path} />
                            </span>
                        </span>
                        {part.path.endsWith("/") ? (
                            <>
                                {part.path.slice(0, -1)}
                                <span className="text-transparent">/</span>
                            </>
                        ) : (
                            part.path
                        )}
                    </mark>
                ),
            )}
        </>
    );
}
