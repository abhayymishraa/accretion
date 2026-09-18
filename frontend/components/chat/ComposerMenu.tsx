import type { MenuChoice, MenuKind } from "@/hooks/chat/useComposerMenu";
import styles from "./transcript.module.css";

interface ComposerMenuProps {
    id: string;
    kind: MenuKind;
    choices: MenuChoice[];
    activeIndex: number;
    onHover: (index: number) => void;
    onPick: (choice: MenuChoice) => void;
}

export function ComposerMenu({
    id,
    kind,
    choices,
    activeIndex,
    onHover,
    onPick,
}: ComposerMenuProps) {
    return (
        <div
            className={`${styles.composerMenu} absolute bottom-[calc(100%+8px)] left-0 z-30 w-full max-w-md overflow-hidden rounded-[10px] border border-border bg-popover p-1 [box-shadow:0_16px_40px_-12px_#000c,0_0_0_1px_#0004]`}
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
                            className="flex w-full items-baseline gap-2 rounded-[7px] px-2.5 py-1.5 text-left aria-selected:bg-secondary"
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
