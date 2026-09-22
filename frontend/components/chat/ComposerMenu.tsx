import type { MenuChoice, MenuKind } from "@/hooks/chat/useComposerMenu";
import styles from "@/components/chat/menu.module.css";

interface ComposerMenuProps {
    id: string;
    open: boolean;
    kind: MenuKind;
    choices: MenuChoice[];
    activeIndex: number;
    onHover: (index: number) => void;
    onPick: (choice: MenuChoice) => void;
}

export function ComposerMenu({
    id,
    open,
    kind,
    choices,
    activeIndex,
    onHover,
    onPick,
}: ComposerMenuProps) {
    return (
        <div
            data-state={open ? "open" : "closed"}
            aria-hidden={!open}
            inert={!open}
            className={`${styles.menu} absolute bottom-[calc(100%+8px)] left-0 z-30 w-full max-w-md origin-bottom-left overflow-hidden rounded-[10px] border border-border bg-surface-2 p-1 [box-shadow:0_16px_40px_-12px_#000000cc]`}
        >
            <ul id={id} role="listbox" aria-label={kind === "files" ? "Project files" : "Commands"}>
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
                            className="flex w-full items-baseline gap-2 rounded-[7px] px-2.5 py-1.5 text-left aria-selected:bg-surface-1"
                        >
                            <span className="shrink-0 text-[13px] text-foreground">
                                {choice.label}
                            </span>
                            {choice.detail ? (
                                <span className="truncate font-mono text-[11px] text-muted-foreground">
                                    {choice.detail}
                                </span>
                            ) : null}
                        </button>
                    </li>
                ))}
            </ul>
            <p className="px-2.5 pt-1.5 pb-1 text-[11px] text-muted-foreground">
                {kind === "files" ? "Enter to reference" : "Enter to insert"}
                <span aria-hidden="true"> · Esc to dismiss</span>
            </p>
        </div>
    );
}
