import { ComposerMenu } from "@/components/chat/ComposerMenu";
import { ModelPicker } from "@/components/chat/ModelPicker";
import { PromptMirror } from "@/components/chat/PromptMirror";
import { useLightTheme } from "@/components/layout/ThemeProvider";
import { Button } from "@/components/ui/button";
import { CometSpinner } from "@/components/ui/comet-spinner";
import { IconSwap } from "@/components/ui/IconSwap";
import { useComposerMenu } from "@/hooks/chat/useComposerMenu";
import { useAccountSkills } from "@/hooks/skills/useAccountSkills";
import { MAX_PROJECT_DRAFT_LENGTH } from "@/lib/projects/draft";
import { starterBriefs } from "@/lib/projects/starterBriefs";
import { ArrowUpIcon } from "@radix-ui/react-icons";
import { ArrowRight, Plus } from "lucide-react";
import type { ModelOption } from "@/types/models.type";
import { BorderBeam } from "border-beam";
import { useEffect, useRef, useState } from "react";

const MENU_ID = "project-brief-menu";
// The mirror and the textarea share one grid cell and must lay text out identically.
const TEXT =
    "col-start-1 row-start-1 pl-[0.2em] text-[16px] leading-[1.6] sm:text-[15px] wrap-anywhere";

interface ChatInputBoxProps {
    input: string;
    isLoading: boolean;
    disabled?: boolean;
    onInputChange: (value: string) => void;
    onSubmit: (e: React.FormEvent) => void;
    models: ModelOption[];
    modelChoice: string;
    onModelChoiceChange: (value: string) => void;
}

/**
 * The first prompt, written like every later one: the workspace composer's "/" menu and skill tags,
 * with the skills the account has on. There are no files yet, and nothing to manage per project.
 */
export function ChatInputBox({
    input,
    isLoading,
    disabled = false,
    onInputChange,
    onSubmit,
    models,
    modelChoice,
    onModelChoiceChange,
}: ChatInputBoxProps) {
    const field = useRef<HTMLTextAreaElement>(null);
    const [showExamples, setShowExamples] = useState(false);
    const controlsDisabled = isLoading || disabled;
    const submitLabel = isLoading ? "Starting your project" : "Start building";
    const { skills, ensureLoaded } = useAccountSkills();
    const menu = useComposerMenu({
        textarea: field,
        value: input,
        onChange: onInputChange,
        files: [],
        skills,
        disabled: controlsDisabled,
    });
    // Skills are fetched the first time "/" is used, not on page load.
    const wantsSkills = menu.kind === "commands";
    useEffect(() => {
        if (wantsSkills) ensureLoaded();
    }, [wantsSkills, ensureLoaded]);
    const light = useLightTheme();

    return (
        <div className="relative animate-in rounded-[16px] text-left fade-in slide-in-from-bottom-3 duration-500 ease-out motion-reduce:animate-none [box-shadow:0_24px_70px_-26px_#00000080]">
            {/* Outside the beam, whose overflow: hidden would clip it. */}
            <ComposerMenu
                open={menu.open}
                id={MENU_ID}
                kind={menu.kind ?? "commands"}
                choices={menu.choices}
                activeIndex={menu.activeIndex}
                onHover={menu.setActiveIndex}
                onPick={menu.accept}
            />
            {/* As in the workspace, the beam rides the border while the project starts. */}
            <BorderBeam
                active={isLoading}
                size="md"
                colorVariant="ocean"
                strength={0.6}
                theme={light ? "light" : "dark"}
                className="w-full rounded-[16px]"
            >
                <form
                    onSubmit={onSubmit}
                    aria-busy={isLoading}
                    className="relative rounded-[16px] border border-border bg-surface-2 px-3.5 pt-3 pb-2 [transition:border-color_180ms_ease] focus-within:border-input"
                >
                    <label htmlFor="project-brief" className="sr-only">
                        Describe your app idea
                    </label>
                    <div className="grid max-h-44 min-h-[2.4em] overflow-y-auto overscroll-contain">
                        {/* The text you see, with picked skills as tags, under a transparent textarea
                            that keeps the caret; it also grows the cell to fit. */}
                        <div
                            aria-hidden="true"
                            className={`${TEXT} whitespace-pre-wrap text-foreground`}
                        >
                            <PromptMirror text={input} files={[]} skills={skills} />{" "}
                        </div>
                        <textarea
                            id="project-brief"
                            ref={field}
                            rows={1}
                            aria-describedby="project-brief-note"
                            className={`${TEXT} w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-transparent caret-foreground outline-none placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed`}
                            placeholder="Hey Accretion, let’s make…"
                            value={input}
                            disabled={controlsDisabled}
                            maxLength={MAX_PROJECT_DRAFT_LENGTH}
                            autoComplete="off"
                            required
                            {...menu.fieldProps(MENU_ID, !!input.trim())}
                        />
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-3">
                        <div className="flex min-w-0 items-center gap-1">
                            <Button
                                type="button"
                                variant="utility"
                                className="h-9 min-w-9 px-2 font-mono pointer-coarse:size-11"
                                disabled={controlsDisabled}
                                aria-label="Use a skill or a ready-made prompt"
                                title="Skills and prompts"
                                onClick={() => menu.openKind("commands")}
                            >
                                /
                            </Button>
                            <Button
                                variant="utility"
                                type="button"
                                disabled={controlsDisabled}
                                className="gap-1.5 px-2"
                                aria-expanded={showExamples}
                                aria-controls="project-brief-examples"
                                onClick={() => setShowExamples(!showExamples)}
                            >
                                <Plus size={16} aria-hidden="true" />
                                <span className="max-sm:sr-only">Examples</span>
                            </Button>
                            <ModelPicker
                                models={models}
                                value={modelChoice}
                                disabled={controlsDisabled}
                                onChange={onModelChoiceChange}
                            />
                        </div>
                        <Button
                            type="submit"
                            variant="send"
                            disabled={controlsDisabled || !input.trim()}
                            className="size-9 shrink-0 rounded-full disabled:bg-surface-3 disabled:text-muted-foreground/50"
                            aria-label={submitLabel}
                            title={submitLabel}
                        >
                            {/* Both icons share one cell so the swap cross-fades instead of cutting. */}
                            <IconSwap
                                swapped={isLoading}
                                from={<ArrowUpIcon className="size-4" aria-hidden="true" />}
                                to={<CometSpinner aria-hidden className="size-[15px]" />}
                            />
                        </Button>
                    </div>
                    <div id="project-brief-examples" data-disclosure={showExamples ? "open" : ""}>
                        <div className="mt-3 grid gap-1 border-t border-hairline pt-3 sm:grid-cols-3">
                            {starterBriefs.map((starter) => (
                                <Button
                                    key={starter.id}
                                    type="button"
                                    variant="utility"
                                    disabled={controlsDisabled}
                                    className="justify-between px-3"
                                    onClick={() => {
                                        onInputChange(starter.prompt);
                                        setShowExamples(false);
                                        field.current?.focus();
                                    }}
                                >
                                    {starter.title}
                                    <ArrowRight size={14} aria-hidden="true" />
                                </Button>
                            ))}
                        </div>
                    </div>
                    <span className="sr-only" role="status">
                        {isLoading
                            ? "Starting your project…"
                            : disabled
                              ? "Loading your account…"
                              : ""}
                    </span>
                </form>
            </BorderBeam>
        </div>
    );
}
