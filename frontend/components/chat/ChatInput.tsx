import { ComposerMenu } from "@/components/chat/ComposerMenu";
import { Button } from "@/components/ui/button";
import { useComposerMenu } from "@/hooks/chat/useComposerMenu";
// Composer structure adapted from Beautiful UI ChatComposer, MIT © 2026 Shane Levine.
// See ../ember/BEAUTIFUL-UI-LICENSE. The parent owns the real run lifecycle.
import { ArrowUpIcon, FileTextIcon, StopIcon } from "@radix-ui/react-icons";
import { useRef } from "react";

const MENU_ID = "chat-prompt-menu";

const modes = [
    { value: "auto" as const, label: "Auto", hint: "Edits the app straight away" },
    { value: "plan" as const, label: "Plan", hint: "Proposes a plan before editing" },
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
    const canCompose = wsConnected && !isBuilding && !awaitingInput;
    const prompt = useRef<HTMLTextAreaElement>(null);
    const menu = useComposerMenu({
        textarea: prompt,
        value: input,
        onChange: onInputChange,
        files,
        disabled: !canCompose,
    });
    const mirror =
        "col-start-1 row-start-1 text-[14.5px] leading-[1.65] max-md:text-[16px] wrap-anywhere";

    return (
        <div className="ember-chat-input border-t border-border bg-surface-1 px-6 py-4 max-md:px-4 max-md:py-3">
            <form
                className="ember-composer relative mx-auto w-full max-w-[46rem] rounded-[14px] border border-border bg-surface-2 px-3 pt-3 pb-2 [transition:border-color_150ms_ease] focus-within:border-input"
                onSubmit={onSubmit}
            >
                <ComposerMenu
                    open={menu.open}
                    id={MENU_ID}
                    kind={menu.kind ?? "files"}
                    choices={menu.choices}
                    activeIndex={menu.activeIndex}
                    onHover={menu.setActiveIndex}
                    onPick={menu.accept}
                />

                <label htmlFor="chat-prompt" className="sr-only">
                    Describe a change to your app
                </label>
                <div className="grid max-h-44 overflow-y-auto overscroll-contain">
                    {/* Mirrors the text so the grid cell, and with it the textarea, grows to fit. */}
                    <div aria-hidden="true" className={`${mirror} invisible whitespace-pre-wrap`}>
                        {input}{" "}
                    </div>
                    <textarea
                        id="chat-prompt"
                        ref={prompt}
                        rows={1}
                        className={`${mirror} w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-foreground outline-none placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed`}
                        value={input}
                        disabled={!canCompose}
                        role="combobox"
                        aria-autocomplete="list"
                        aria-expanded={menu.open}
                        aria-controls={menu.open ? MENU_ID : undefined}
                        aria-activedescendant={
                            menu.open ? `${MENU_ID}-${menu.activeIndex}` : undefined
                        }
                        onChange={(event) => {
                            onInputChange(event.target.value);
                            menu.syncFromEvent(event.currentTarget);
                        }}
                        onClick={(event) => menu.syncFromEvent(event.currentTarget)}
                        onBlur={menu.close}
                        onKeyUp={(event) => {
                            if (event.key.startsWith("Arrow") || event.key === "Home")
                                menu.syncFromEvent(event.currentTarget);
                        }}
                        onKeyDown={(event) => {
                            if (menu.handleKeyDown(event)) return;
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
                    />
                </div>

                <div className="ember-composer-footer mt-2 flex items-center gap-2">
                    <div className="transcript-composerTools flex items-center gap-0.5">
                        <Button
                            type="button"
                            variant="utility"
                            className="h-8 min-h-8 min-w-8 gap-1.5 px-2"
                            disabled={!canCompose}
                            aria-label="Reference a project file"
                            onClick={() => menu.openKind("files")}
                        >
                            <FileTextIcon aria-hidden="true" />
                            <span aria-hidden="true">@</span>
                        </Button>
                        <Button
                            type="button"
                            variant="utility"
                            className="h-8 min-h-8 min-w-8 px-2 font-mono"
                            disabled={!canCompose}
                            aria-label="Insert a command"
                            onClick={() => menu.openKind("commands")}
                        >
                            /
                        </Button>
                    </div>

                    <fieldset
                        disabled={isBuilding || awaitingInput}
                        className="relative flex rounded-[8px] bg-surface-3 p-[3px] disabled:opacity-40"
                    >
                        <legend className="sr-only">Request mode</legend>
                        <span
                            aria-hidden="true"
                            className="absolute top-[3px] bottom-[3px] w-[calc(50%-3px)] rounded-[6px] bg-surface-1 ring-1 ring-hairline transition-transform duration-200 ease-[var(--ease-out)] motion-reduce:transition-none"
                            style={{ transform: `translateX(${mode === "auto" ? "0%" : "100%"})` }}
                        />
                        {modes.map((item) => (
                            <label
                                key={item.value}
                                title={item.hint}
                                className={`relative z-10 flex h-[25px] min-w-[58px] cursor-pointer items-center justify-center rounded-[6px] px-2.5 text-[12.5px] transition-colors duration-150 ease-out has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring has-[:focus-visible]:outline-offset-1 ${
                                    mode === item.value
                                        ? "text-foreground"
                                        : "text-muted-foreground pointer-fine:hover:text-foreground"
                                }`}
                            >
                                <input
                                    type="radio"
                                    name="chat-mode"
                                    className="sr-only"
                                    checked={mode === item.value}
                                    onChange={() => onModeChange(item.value)}
                                />
                                {item.label}
                            </label>
                        ))}
                    </fieldset>

                    <div className="ml-auto flex items-center gap-2">
                        <ConnectionPill
                            connected={wsConnected}
                            building={isBuilding}
                            awaiting={awaitingInput}
                        />
                        {isBuilding ? (
                            <Button
                                type="button"
                                variant="utility"
                                className="gap-1.5 border border-border bg-surface-1 px-3 text-[12.5px] text-foreground"
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
                                className="rounded-full disabled:bg-surface-3 disabled:text-muted-foreground/50"
                                disabled={!canCompose || !input.trim()}
                                aria-label="Send message"
                            >
                                <ArrowUpIcon />
                            </Button>
                        )}
                    </div>
                </div>
            </form>
        </div>
    );
}

/** Steady state is the boring one, so it stays muted. Only trouble takes colour. */
function ConnectionPill({
    connected,
    building,
    awaiting,
}: {
    connected: boolean;
    building: boolean;
    awaiting: boolean;
}) {
    const [label, dot, tone] = !connected
        ? ["Offline", "bg-destructive", "border-destructive/40 text-destructive"]
        : building
          ? ["Working", "bg-primary", "border-hairline text-foreground"]
          : awaiting
            ? ["Your turn", "bg-primary", "border-hairline text-foreground"]
            : ["Live", "bg-muted-foreground/50", "border-transparent text-muted-foreground"];
    return (
        <span
            className={`ember-connection inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-[11px] ${tone}`}
            role="status"
        >
            <span
                aria-hidden="true"
                className={`size-1.5 rounded-full ${dot} ${
                    building || !connected ? "motion-safe:animate-pulse" : ""
                }`}
            />
            {label}
        </span>
    );
}
