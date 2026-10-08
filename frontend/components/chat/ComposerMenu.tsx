import type { MenuChoice, MenuKind } from "@/hooks/chat/useComposerMenu";
import styles from "@/components/chat/menu.module.css";
import { FileIcon } from "@/components/files/FileIcon";
import { ServiceIcon } from "@/components/mcp/ServiceLogo";
import type { PromptCategory } from "@/lib/chat/prompts";
import {
    Accessibility,
    Gauge,
    Hand,
    Lock,
    Plug,
    ScrollText,
    Search,
    Settings2,
    Sparkles,
    Workflow,
    type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

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

// One icon per prompt category, so a prompt row reads like a skill row but says what it is for.
const PROMPT_ICONS: Record<PromptCategory, LucideIcon> = {
    Accessibility,
    SEO: Search,
    Usability: Hand,
    Performance: Gauge,
    General: Sparkles,
    Workflow,
};

/** The highlighted skill or prompt in full, beside the list. */
function Detail({ choice, open }: { choice: MenuChoice; open: boolean }) {
    const { skill, service } = choice;
    if (!skill && !service && !choice.category) return null;
    return (
        // Moves with the menu: same styles, same open state.
        <aside
            data-state={open ? "open" : "closed"}
            aria-hidden="true"
            inert={!open}
            className={`${styles.menu} pointer-events-auto hidden origin-bottom-left max-h-[min(45dvh,20rem)] w-[17rem] shrink-0 flex-col overflow-y-auto overscroll-contain rounded-[10px] border border-border bg-surface-2 [box-shadow:0_16px_40px_-12px_#000000cc] md:flex`}
        >
            <div className="border-b border-hairline px-3.5 py-2.5">
                <p className="truncate text-[12.5px] text-foreground">
                    {skill || service ? (
                        <span className="font-mono">/{choice.label}</span>
                    ) : (
                        choice.label
                    )}
                </p>
                <p className="mt-0.5 flex items-center gap-1 text-[11px] text-muted-foreground">
                    {choice.group} › {choice.subgroup}
                    {skill?.required && (
                        <>
                            <Lock size={10} className="ml-1" />
                            Required
                        </>
                    )}
                </p>
            </div>
            <p className="px-3.5 py-3 text-[12.5px] leading-[1.55] text-muted-foreground">
                {skill
                    ? skill.description
                    : service
                      ? `${service.title}. ${service.description || `${service.tool_count} tools`}`
                      : choice.insert}
            </p>
        </aside>
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
    // Opens the workspace tab for skills or connectors. Absent where there is no project (the new project page).
    onManage?: (tab: "skills" | "connectors") => void;
}

// The menu's ways out to the workspace tabs that turn "/" choices on and off.
const MANAGE = [
    { tab: "skills", label: "Manage skills", icon: Settings2 },
    { tab: "connectors", label: "Manage connectors", icon: Plug },
] as const;

export function ComposerMenu({
    id,
    open,
    kind,
    choices,
    activeIndex,
    onHover,
    onPick,
    onManage,
}: ComposerMenuProps) {
    // The list scrolls; keep the row the arrow keys reach in view. Headings sit between rows, so
    // the row is found by its id, not its position.
    useEffect(() => {
        if (open)
            document.getElementById(`${id}-${activeIndex}`)?.scrollIntoView({ block: "nearest" });
    }, [open, activeIndex, id]);
    // Picking clears the choices at once; the panel keeps the last one so it can fade out with the
    // menu instead of vanishing.
    const active = choices[activeIndex];
    const [shown, setShown] = useState(active);
    if (active && active.id !== shown?.id) setShown(active);
    return (
        // Takes no clicks itself: the closed menu is invisible, and the chat under it stays usable. The
        // side panel may reach past the chat into the preview.
        <div className="pointer-events-none absolute bottom-[calc(100%+8px)] left-0 z-30 w-full">
            <div className="flex items-end gap-2">
                <div
                    data-state={open ? "open" : "closed"}
                    aria-hidden={!open}
                    inert={!open}
                    className={`${styles.menu} pointer-events-auto w-[min(100%,28rem)] shrink-0 origin-bottom-left overflow-hidden rounded-[10px] border border-border bg-surface-2 p-1 [box-shadow:0_16px_40px_-12px_#000000cc]`}
                >
                    <ul
                        id={id}
                        role="listbox"
                        aria-label={kind === "files" ? "Project files" : "Commands and skills"}
                        className="max-h-[min(45dvh,20rem)] overflow-y-auto overscroll-contain"
                    >
                        {choices.map((choice, index) => {
                            const previous = choices[index - 1];
                            const Icon = choice.skill
                                ? ScrollText
                                : choice.category && PROMPT_ICONS[choice.category];
                            const newGroup = choice.group && choice.group !== previous?.group;
                            const newSubgroup =
                                choice.subgroup &&
                                (newGroup || choice.subgroup !== previous?.subgroup);
                            return (
                                <li key={choice.id} role="presentation">
                                    {newGroup && (
                                        <p className="px-2.5 pt-2.5 pb-1 text-[11.5px] font-medium text-foreground">
                                            {choice.group}
                                        </p>
                                    )}
                                    {newSubgroup && (
                                        <p className="px-2.5 pt-1 pb-0.5 text-[11px] text-muted-foreground">
                                            {choice.subgroup}
                                        </p>
                                    )}
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
                                        {choice.service && (
                                            <ServiceIcon
                                                id={choice.service.name}
                                                icon={choice.service.icon}
                                                className="size-4 text-muted-foreground"
                                            />
                                        )}
                                        {Icon && (
                                            <Icon
                                                aria-hidden="true"
                                                className="size-4 shrink-0 text-muted-foreground"
                                            />
                                        )}
                                        <span className="shrink-0 text-[13px] text-foreground">
                                            <Label choice={choice} />
                                        </span>
                                        {choice.detail ? (
                                            // From tablet width the side panel shows it; screen readers keep it here.
                                            <span
                                                className={`min-w-0 truncate font-mono text-[11px] text-muted-foreground ${choice.skill ? "md:sr-only" : ""}`}
                                            >
                                                {choice.detail}
                                            </span>
                                        ) : null}
                                    </button>
                                </li>
                            );
                        })}
                    </ul>
                    {kind === "commands" && onManage && (
                        <div className="mt-1 grid grid-cols-2 gap-1 border-t border-hairline pt-1">
                            {MANAGE.map(({ tab, label, icon: Icon }) => (
                                <button
                                    key={tab}
                                    type="button"
                                    // Keeps the menu from closing on blur before the click lands.
                                    onMouseDown={(event) => event.preventDefault()}
                                    onClick={() => onManage(tab)}
                                    className="flex h-9 w-full items-center gap-2 rounded-[7px] px-2.5 text-left text-[13px] text-muted-foreground pointer-coarse:h-11 pointer-fine:hover:bg-surface-1 pointer-fine:hover:text-foreground"
                                >
                                    <Icon aria-hidden="true" className="size-4 shrink-0" />
                                    <span className="truncate">{label}</span>
                                </button>
                            ))}
                        </div>
                    )}
                    <p className="px-2.5 pt-1.5 pb-1 text-[11px] text-muted-foreground">
                        {kind === "files" ? "Enter to reference" : "Enter to insert"}
                        <span aria-hidden="true"> · Esc to dismiss</span>
                    </p>
                </div>
                {shown && <Detail choice={shown} open={open} />}
            </div>
        </div>
    );
}
