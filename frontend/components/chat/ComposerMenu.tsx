import type { MenuChoice, MenuKind } from "@/hooks/chat/useComposerMenu";
import styles from "@/components/chat/menu.module.css";
import { FileIcon } from "@/components/files/FileIcon";
import { ScrollText, Settings2 } from "lucide-react";
import { useEffect, useRef } from "react";

/** The label with the typed query picked out, as editors' quick-open lists do. */
function Label({ choice }: { choice: MenuChoice }) {
    if (!choice.match) return <>{choice.label}</>;
    const [start, end] = choice.match;
    return (
        <>
            {choice.label.slice(0, start)}
            <span className="text-accent-foreground">{choice.label.slice(start, end)}</span>
            {choice.label.slice(end)}
        </>
    );
}

interface ComposerMenuProps {
    id: string;
    open: boolean;
    kind: MenuKind;
    choices: MenuChoice[];
    activeIndex: number;
    onHover: (index: number) => void;
    onPick: (choice: MenuChoice) => void;
    onManageSkills: () => void;
}

export function ComposerMenu({
    id,
    open,
    kind,
    choices,
    activeIndex,
    onHover,
    onPick,
    onManageSkills,
}: ComposerMenuProps) {
    const list = useRef<HTMLUListElement>(null);
    // The skills list scrolls; keep the row the arrow keys reach in view.
    useEffect(() => {
        if (open) list.current?.children[activeIndex]?.scrollIntoView({ block: "nearest" });
    }, [open, activeIndex]);
    return (
        <div
            data-state={open ? "open" : "closed"}
            aria-hidden={!open}
            inert={!open}
            className={`${styles.menu} absolute bottom-[calc(100%+8px)] left-0 z-30 w-full max-w-md origin-bottom-left overflow-hidden rounded-[10px] border border-border bg-surface-2 p-1 [box-shadow:0_16px_40px_-12px_#000000cc]`}
        >
            <ul
                ref={list}
                id={id}
                role="listbox"
                aria-label={kind === "files" ? "Project files" : "Commands and skills"}
                className="max-h-[min(45dvh,20rem)] overflow-y-auto overscroll-contain"
            >
                {choices.map((choice, index) => (
                    <li key={choice.id}>
                        <button
                            type="button"
                            role="option"
                            id={`${id}-${index}`}
                            aria-selected={index === activeIndex}
                            tabIndex={-1}
                            // Keeps focus in the textarea so typing never breaks mid-selection.
                            onMouseDown={(event) => event.preventDefault()}
                            onMouseMove={() => onHover(index)}
                            onClick={() => onPick(choice)}
                            className="flex w-full min-w-0 items-center gap-2.5 rounded-[7px] px-2.5 py-1.5 text-left aria-selected:bg-surface-1"
                        >
                            {kind === "files" && <FileIcon filename={choice.label} />}
                            {choice.skill && (
                                <ScrollText
                                    aria-hidden="true"
                                    className="size-4 shrink-0 text-muted-foreground"
                                />
                            )}
                            <span className="shrink-0 text-[13px] text-foreground">
                                <Label choice={choice} />
                            </span>
                            {choice.detail ? (
                                <span className="min-w-0 truncate font-mono text-[11px] text-muted-foreground">
                                    {choice.detail}
                                </span>
                            ) : null}
                        </button>
                    </li>
                ))}
            </ul>
            {kind === "commands" && (
                <button
                    type="button"
                    // Keeps the menu from closing on blur before the click lands.
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={onManageSkills}
                    className="mt-1 flex h-9 w-full items-center gap-2.5 rounded-[7px] border-t border-hairline px-2.5 text-left text-[13px] text-muted-foreground pointer-coarse:h-11 pointer-fine:hover:bg-surface-1 pointer-fine:hover:text-foreground"
                >
                    <Settings2 aria-hidden="true" className="size-4" />
                    Manage skills
                </button>
            )}
            <p className="px-2.5 pt-1.5 pb-1 text-[11px] text-muted-foreground">
                {kind === "files" ? "Enter to reference" : "Enter to insert"}
                <span aria-hidden="true"> · Esc to dismiss</span>
            </p>
        </div>
    );
}
