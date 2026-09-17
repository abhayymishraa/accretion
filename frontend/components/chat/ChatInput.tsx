import { Button } from "@/components/ui/button";
// Composer structure adapted from Beautiful UI ChatComposer, MIT © 2026 Shane Levine.
// See ../ember/BEAUTIFUL-UI-LICENSE. The parent owns the real run lifecycle.
import {
    ArrowUpIcon,
    Cross2Icon,
    FileTextIcon,
    MagnifyingGlassIcon,
    StopIcon,
} from "@radix-ui/react-icons";
import { useRef, useState } from "react";

const commands = [
    {
        name: "Improve layout",
        prompt: "Improve the layout and spacing of this app. ",
    },
    {
        name: "Check accessibility",
        prompt: "Review and improve the accessibility of this app. ",
    },
    { name: "Fix an issue", prompt: "Fix this issue in my app: " },
    { name: "Explain the code", prompt: "Explain how the current app works. " },
];

interface ChatInputProps {
    files?: string[];
    input: string;
    wsConnected: boolean;
    isBuilding: boolean;
    onInputChange: (value: string) => void;
    onSubmit: (e: React.FormEvent) => void;
    onCancel: () => void;
    canCancel: boolean;
    awaitingInput?: boolean;
    mode: "auto" | "plan";
    onModeChange: (mode: "auto" | "plan") => void;
}

export function ChatInput({
    files = [],
    input,
    wsConnected,
    isBuilding,
    onInputChange,
    onSubmit,
    onCancel,
    canCancel,
    awaitingInput = false,
    mode,
    onModeChange,
}: ChatInputProps) {
    const [menu, setMenu] = useState<"files" | "commands" | null>(null);
    const [query, setQuery] = useState("");
    const textarea = useRef<HTMLTextAreaElement>(null);
    const canCompose = wsConnected && !isBuilding && !awaitingInput;
    const normalizedQuery = query.toLowerCase();
    const choices = (
        menu === "files" ? files.map((file) => ({ name: file, prompt: `@${file} ` })) : commands
    ).filter((item) => item.name.toLowerCase().includes(normalizedQuery));
    const closeMenu = () => {
        setMenu(null);
        setQuery("");
        textarea.current?.focus();
    };
    const openMenu = (next: "files" | "commands") => {
        setMenu(next);
        setQuery("");
    };
    return (
        <div className="ember-chat-input border-t border-border py-3 px-[15px] bg-card">
            <form
                className="ember-composer border border-border bg-secondary rounded-[10px] p-3 flex flex-col gap-3 focus-within:border-ring transcript-composer relative [&_.ember-send]:min-w-11 [&_.ember-send]:min-h-11 [&_.ember-composer-footer]:gap-2"
                onSubmit={onSubmit}
            >
                {menu && canCompose && (
                    <div
                        className="transcript-menu absolute bottom-[calc(100%_+_8px)] left-0 right-0 z-20 p-2.5 border border-border bg-card rounded-[6px] [box-shadow:0_8px_28px_#0005]"
                        role="dialog"
                        aria-label={
                            menu === "files" ? "Reference project files" : "Prompt commands"
                        }
                        onKeyDown={(event) => {
                            if (event.key === "Escape") {
                                event.preventDefault();
                                closeMenu();
                            }
                        }}
                    >
                        <div className="transcript-menuHeader flex items-center gap-2 [&_input]:min-w-0 [&_input]:flex-1 [&_input]:bg-transparent [&_input]:border-0 [&_input]:outline-none [&_input]:text-[13px] [&_input]:text-foreground">
                            <MagnifyingGlassIcon aria-hidden="true" />
                            <input
                                autoFocus
                                value={query}
                                onChange={(event) => setQuery(event.target.value)}
                                aria-label={
                                    menu === "files" ? "Search project files" : "Search commands"
                                }
                                placeholder={
                                    menu === "files" ? "Search project files…" : "Search commands…"
                                }
                                onKeyDown={(event) => {
                                    if (event.key === "Enter") event.preventDefault();
                                }}
                            />
                            <Button
                                variant="utility"
                                type="button"
                                onClick={closeMenu}
                                aria-label="Close search"
                            >
                                <Cross2Icon />
                            </Button>
                        </div>
                        <div className="transcript-options max-h-[min(240px,_30dvh)] overflow-auto mt-[5px]">
                            {choices.map((item) => (
                                <button
                                    type="button"
                                    className="transcript-option w-full text-left block min-h-11 p-2 border-0 rounded-[3px] bg-transparent text-secondary-foreground text-[12px] wrap-anywhere cursor-pointer [&:hover]:bg-secondary [&:hover]:text-foreground [&:focus-visible]:bg-secondary [&:focus-visible]:text-foreground [&:focus-visible]:outline-2 [&:focus-visible]:outline-solid [&:focus-visible]:outline-primary [&:focus-visible]:outline-offset-0.5"
                                    key={item.name}
                                    onClick={() => {
                                        onInputChange(
                                            `${input}${input && !/\s$/.test(input) ? " " : ""}${item.prompt}`,
                                        );
                                        closeMenu();
                                    }}
                                >
                                    {item.name}
                                </button>
                            ))}
                            {!choices.length && (
                                <p className="transcript-empty text-[12px] text-muted-foreground py-3 px-2">
                                    {menu === "files" && !files.length
                                        ? "Saved files will appear after your first build."
                                        : "No matches. Try a different search."}
                                </p>
                            )}
                        </div>
                        <p className="transcript-caption font-mono text-[11px] text-muted-foreground">
                            {menu === "files"
                                ? "Adds a file reference to your message."
                                : "Choose a starting prompt. Edit it before sending."}
                        </p>
                    </div>
                )}
                <label htmlFor="chat-prompt" className="sr-only">
                    Describe a change to your app
                </label>
                <textarea
                    className="w-full min-h-12 text-[14px] max-h-52.5 resize-y border-0 bg-transparent text-foreground leading-[1.65] outline-none placeholder:text-muted-foreground focus-visible:outline-none max-md:text-[16px]"
                    ref={textarea}
                    id="chat-prompt"
                    value={input}
                    onChange={(event) => onInputChange(event.target.value)}
                    onKeyDown={(event) => {
                        if (
                            event.key === "Enter" &&
                            !event.shiftKey &&
                            !event.nativeEvent.isComposing
                        ) {
                            event.preventDefault();
                            if (canCompose && input.trim())
                                event.currentTarget.form?.requestSubmit();
                        }
                    }}
                    placeholder={
                        awaitingInput
                            ? "Answer or dismiss the proposal above to continue"
                            : "Describe a change to your app…"
                    }
                    disabled={!canCompose}
                    rows={2}
                />
                <div className="ember-composer-footer flex items-center justify-between gap-[15px] [&>span]:text-[11px] [&>span]:text-muted-foreground">
                    <div className="transcript-composerTools flex gap-0.5 items-center">
                        <Button
                            type="button"
                            variant="utility"
                            disabled={!canCompose}
                            aria-label="Reference project files"
                            aria-expanded={menu === "files"}
                            onClick={() => openMenu("files")}
                        >
                            <FileTextIcon aria-hidden="true" />
                            <span>@</span>
                        </Button>
                        <Button
                            type="button"
                            variant="utility"
                            disabled={!canCompose}
                            aria-label="Prompt commands"
                            aria-expanded={menu === "commands"}
                            onClick={() => openMenu("commands")}
                        >
                            /
                        </Button>
                        <label className="flex items-center gap-1 text-xs text-muted-foreground">
                            <span className="sr-only">Request mode</span>
                            <select
                                aria-label="Request mode"
                                value={mode}
                                disabled={isBuilding || awaitingInput}
                                onChange={(event) =>
                                    onModeChange(event.target.value as "auto" | "plan")
                                }
                                className="min-h-9 rounded border border-input bg-card px-2 text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                            >
                                <option value="auto">Auto</option>
                                <option value="plan">Plan first</option>
                            </select>
                        </label>
                    </div>
                    <span
                        className="ember-connection text-[10px] text-muted-foreground data-[connected=true]:text-accent-foreground"
                        data-connected={wsConnected}
                    >
                        {isBuilding
                            ? "Working on your app"
                            : wsConnected
                              ? "Connected"
                              : "Reconnecting to your project…"}
                    </span>
                    {isBuilding ? (
                        <Button
                            type="button"
                            variant="default"
                            onClick={onCancel}
                            disabled={!canCancel}
                            aria-label="Stop the current run"
                        >
                            <StopIcon />
                            Stop
                        </Button>
                    ) : (
                        <Button
                            type="submit"
                            variant="send"
                            disabled={!canCompose || !input.trim()}
                            aria-label="Send message"
                        >
                            <ArrowUpIcon />
                        </Button>
                    )}
                </div>
            </form>
        </div>
    );
}
