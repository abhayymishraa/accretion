import { ModelPicker } from "@/components/chat/ModelPicker";
import { Button } from "@/components/ui/button";
import { IconSwap } from "@/components/ui/IconSwap";
import { Input } from "@/components/ui/input";
import { MAX_PROJECT_DRAFT_LENGTH } from "@/lib/projects/draft";
import { starterBriefs } from "@/lib/projects/starterBriefs";
import { ArrowRight, ArrowUp, Loader2, Plus } from "lucide-react";
import type { ModelOption } from "@/types/models.type";
import { useRef, useState } from "react";

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
    const field = useRef<HTMLInputElement>(null);
    const [showExamples, setShowExamples] = useState(false);
    const controlsDisabled = isLoading || disabled;
    const submitLabel = isLoading ? "Starting your project" : "Start building";

    return (
        <form
            onSubmit={onSubmit}
            aria-busy={isLoading}
            className="relative animate-in rounded-[16px] border border-border bg-surface-2 p-3 text-left fade-in slide-in-from-bottom-3 duration-500 ease-out [transition:border-color_180ms_ease] focus-within:border-input motion-reduce:animate-none sm:p-4 [box-shadow:0_24px_70px_-26px_#00000080]"
        >
            <label htmlFor="project-brief" className="sr-only">
                Describe your app idea
            </label>
            <Input
                ref={field}
                id="project-brief"
                aria-describedby="project-brief-note"
                className="h-12 border-0 bg-transparent px-2 text-base shadow-none focus-visible:ring-0 sm:text-lg"
                placeholder="Hey Accretion, let’s make…"
                value={input}
                onChange={(event) => onInputChange(event.target.value)}
                disabled={controlsDisabled}
                maxLength={MAX_PROJECT_DRAFT_LENGTH}
                autoComplete="off"
                required
            />
            <div className="mt-2 flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                    <Button
                        variant="utility"
                        type="button"
                        disabled={controlsDisabled}
                        className="gap-2 px-2"
                        aria-expanded={showExamples}
                        aria-controls="project-brief-examples"
                        onClick={() => setShowExamples(!showExamples)}
                    >
                        <Plus size={16} aria-hidden="true" /> Start with an example
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
                    disabled={controlsDisabled || !input.trim()}
                    className="size-11 shrink-0 rounded-full p-0"
                    aria-label={submitLabel}
                    title={submitLabel}
                >
                    {/* Both icons share one cell so the swap cross-fades instead of cutting. */}
                    <IconSwap
                        swapped={isLoading}
                        from={<ArrowUp size={19} aria-hidden="true" />}
                        to={
                            <Loader2
                                size={19}
                                aria-hidden="true"
                                className={
                                    isLoading
                                        ? "animate-spin motion-reduce:animate-none"
                                        : undefined
                                }
                            />
                        }
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
                {isLoading ? "Starting your project…" : disabled ? "Loading your account…" : ""}
            </span>
        </form>
    );
}
