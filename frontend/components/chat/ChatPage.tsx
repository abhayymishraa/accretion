"use client";

import { ChatInputBox } from "@/components/chat/ChatInputBox";
import { Brand } from "@/components/layout/Brand";
import { ChatNavbar } from "@/components/layout/ChatNavbar";
import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { useNewProject } from "@/hooks/chat/useNewProject";

export default function ChatPage() {
    const {
        input,
        setInput,
        isLoading,
        error,
        isAuthenticated,
        userData,
        handleSignOut,
        handleSubmit,
        models,
        modelChoice,
        setModelChoice,
    } = useNewProject();
    return (
        <div className="ember-chat-home flex h-dvh flex-col overflow-hidden [&>.ember-workspace-header]:shrink-0">
            <ChatNavbar
                isAuthenticated={isAuthenticated}
                userData={userData}
                onSignOut={handleSignOut}
            />
            <div className="ember-workspace-shell flex min-h-0 flex-1 overflow-hidden">
                <WorkspaceSidebar current="new" />
                <main
                    id="main-content"
                    className="relative min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain bg-background"
                >
                    <section
                        className="ember-stage relative isolate flex min-h-full flex-col items-center px-5 pt-[clamp(24px,5dvh,64px)] pb-6 text-center sm:px-10"
                        aria-labelledby="start-heading"
                    >
                        <div className="relative mx-auto flex w-full max-w-5xl flex-1 flex-col items-center">
                            <header className="flex w-full flex-col items-center">
                                <Brand />
                                <h1
                                    id="start-heading"
                                    className="mt-8 max-w-4xl text-[clamp(38px,5.5vw,68px)] font-normal leading-[1.08] tracking-[-.055em] text-balance"
                                >
                                    Talk your next idea{" "}
                                    <span className="text-accent-foreground">into life.</span>
                                </h1>
                                <p className="mt-5 max-w-sm text-base leading-relaxed text-muted-foreground sm:max-w-none">
                                    A conversation. A little direction. Something that’s yours.
                                </p>
                                <div className="mt-7 inline-flex items-center gap-4 rounded-[16px] border border-border bg-surface-2 p-1.5 pl-5">
                                    <span className="text-left text-xs leading-snug text-muted-foreground">
                                        From a thought
                                        <br />
                                        to a first draft.
                                    </span>
                                    <Button
                                        disabled={!isAuthenticated || isLoading}
                                        onClick={() =>
                                            document.getElementById("project-brief")?.focus()
                                        }
                                        className="rounded-[11px] px-5"
                                    >
                                        Try an idea <ArrowRight size={15} aria-hidden="true" />
                                    </Button>
                                </div>
                            </header>
                            <div className="relative mt-[clamp(40px,calc(20dvh_-_48px),152px)] w-full max-w-2xl">
                                <div
                                    className="pointer-events-none absolute -inset-x-4 top-6 h-56 rounded-t-xl border border-border/50 [mask-image:linear-gradient(#0008,transparent_92%)] lg:-inset-x-20"
                                    aria-hidden="true"
                                >
                                    <div className="flex h-8 items-center gap-1.5 border-b border-border/50 px-4">
                                        <span className="size-1.5 rounded-full border border-border" />
                                        <span className="size-1.5 rounded-full border border-border" />
                                        <span className="size-1.5 rounded-full border border-border" />
                                        <span className="ml-3 h-5 w-28 rounded-t border border-border/60" />
                                    </div>
                                </div>
                                <ChatInputBox
                                    input={input}
                                    isLoading={isLoading}
                                    disabled={!isAuthenticated}
                                    onInputChange={setInput}
                                    onSubmit={handleSubmit}
                                    models={models}
                                    modelChoice={modelChoice}
                                    onModelChoiceChange={setModelChoice}
                                />
                                <div className="relative text-left [&>[data-error-box]]:mt-4">
                                    <ErrorBox message={error} />
                                </div>
                                <p
                                    id="project-brief-note"
                                    className="relative mt-5 text-xs leading-relaxed text-muted-foreground"
                                >
                                    Describe your app, then press Enter to start building.
                                </p>
                            </div>
                            <div className="relative mt-auto pt-10">
                                <Link
                                    href="/projects"
                                    className="inline-flex min-h-11 items-center gap-2 text-xs text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-4"
                                >
                                    Continue an existing project{" "}
                                    <ArrowUpRight size={14} aria-hidden="true" />
                                </Link>
                            </div>
                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}
