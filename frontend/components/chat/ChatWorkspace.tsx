"use client";

import { Button } from "@/components/ui/button";
import { CometSpinner } from "@/components/ui/comet-spinner";
import { ErrorBox } from "@/components/ui/ErrorBox";

import { ChatIdHeader } from "@/components/chat/ChatIdHeader";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { OpenFileContext } from "@/components/chat/OpenFileContext";
import { PreviewPanel } from "@/components/chat/PreviewPanel";
import { ProjectTitle } from "@/components/chat/ProjectTitle";
import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { Sparkles } from "lucide-react";
import { ThinkingOrb } from "thinking-orbs";

import { useChatWorkspace } from "@/hooks/chat/useChatWorkspace";
import { mentionTargets } from "@/hooks/chat/useComposerMenu";
import { useProjectSkills } from "@/hooks/skills/useProjectSkills";
import { useEffect, useState } from "react";

// A "/name" in an earlier request: the history needs the project's skills to show it as a pill.
const PICKED_SKILL = /(^|\s)\/[a-z0-9]/;
export default function ChatWorkspace({ chatId }: { chatId: string }) {
    const {
        router,
        connected,
        messages,
        error,
        input,
        setInput,
        mode,
        setMode,
        awaitingInput,
        pendingKind,
        pendingDecisionId,
        isLoading,
        hasOlder,
        loadingOlder,
        loadOlder,
        refreshHistory,
        decided,
        appUrl,
        revisionId,
        isBuilding,
        runId,
        previewWidth,
        setPreviewWidth,
        resizeHandlers,
        showPreview,
        setShowPreview,
        userData,
        signOut,
        models,
        modelChoice,
        setModelChoice,
        mobilePane,
        setMobilePane,
        projectFiles,
        previewTab,
        setPreviewTab,
        openedFile,
        openFile,
        workspaceVisible,
        preview,
        handleConversationScroll,
        trackRef,
        conversationRef,
        containerRef,
        handleSendMessage,
        handleCancel,
    } = useChatWorkspace(chatId);
    // Panel toggle: the preview takes the whole width while the conversation is folded away.
    const [chatHidden, setChatHidden] = useState(false);
    const projectSkills = useProjectSkills(chatId);
    const { ensureLoaded } = projectSkills;
    const usesSkill = messages.some(
        (message) => message.role === "user" && PICKED_SKILL.test(message.content),
    );
    useEffect(() => {
        if (usesSkill) ensureLoaded();
    }, [usesSkill, ensureLoaded]);
    const pills = {
        targets: new Set(mentionTargets(projectFiles)),
        skills: new Set((projectSkills.skills ?? []).map((skill) => skill.name)),
    };
    return (
        <OpenFileContext value={openFile}>
            <div className="relative flex h-dvh min-h-0 flex-col overflow-hidden bg-background">
                <ChatIdHeader
                    userData={userData}
                    showPreview={showPreview}
                    onTogglePreview={() => {
                        setShowPreview(!showPreview);
                        setMobilePane("chat");
                    }}
                    onNewChat={() => router.push("/chat")}
                    onBack={() => router.push("/projects")}
                />
                <div
                    className="hidden max-md:flex max-md:gap-1 max-md:border-b max-md:border-b-border max-md:px-3 max-md:py-1.5 max-md:[&>button]:flex-1"
                    role="group"
                    aria-label="Workspace view"
                >
                    <Button
                        variant="tab"
                        aria-pressed={mobilePane === "chat"}
                        onClick={() => setMobilePane("chat")}
                    >
                        Chat
                    </Button>
                    <Button
                        variant="tab"
                        aria-pressed={mobilePane === "preview"}
                        onClick={() => {
                            setShowPreview(true);
                            setMobilePane("preview");
                        }}
                    >
                        Workspace
                    </Button>
                </div>
                <div className="flex min-h-0 flex-1 max-[1101px]:[&>.ember-workspace-sidebar]:hidden">
                    <WorkspaceSidebar userData={userData} onSignOut={signOut} />
                    <main
                        ref={containerRef}
                        className="[&[data-resizing]_iframe]:pointer-events-none flex min-h-0 flex-1 gap-px overflow-hidden bg-border max-md:gap-0 max-md:[&[data-mobile-pane=chat]>.ember-preview]:hidden max-md:[&[data-mobile-pane=preview]>.ember-conversation]:hidden max-md:[&>.ember-preview]:w-full! max-md:[&>.ember-conversation]:w-full!"
                        data-mobile-pane={mobilePane}
                        id="main-content"
                    >
                        <section
                            className={`ember-conversation flex min-h-0 min-w-0 flex-col bg-surface-1 ${chatHidden ? "md:hidden" : ""}`}
                            aria-label="Project conversation"
                            style={{ width: showPreview ? `${100 - previewWidth}%` : "100%" }}
                        >
                            <div className="flex h-11 shrink-0 items-center border-b border-b-border bg-background px-3 max-md:hidden">
                                <ProjectTitle projectId={chatId} revisionId={revisionId} />
                            </div>
                            <div
                                className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-8 [overflow-anchor:none] max-md:px-4 max-md:py-5"
                                ref={conversationRef}
                                onScroll={handleConversationScroll}
                            >
                                <div
                                    className="mx-auto flex w-full max-w-[46rem] flex-col gap-7"
                                    ref={trackRef}
                                >
                                    {isLoading && (
                                        <div
                                            className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[13px] text-muted-foreground"
                                            role="status"
                                        >
                                            <CometSpinner
                                                aria-hidden
                                                className="size-7 text-primary"
                                            />
                                            Loading messages…
                                        </div>
                                    )}
                                    {hasOlder && (
                                        <Button
                                            variant="utility"
                                            className="self-center"
                                            disabled={loadingOlder}
                                            onClick={loadOlder}
                                        >
                                            {loadingOlder
                                                ? "Loading older messages…"
                                                : "Show earlier"}
                                        </Button>
                                    )}
                                    <ErrorBox message={error ?? ""}>
                                        <Button
                                            variant="utility"
                                            className="text-destructive"
                                            onClick={refreshHistory}
                                        >
                                            Retry
                                        </Button>
                                    </ErrorBox>
                                    {!messages.length && !isLoading && !error && (
                                        <div className="pt-2 pb-4">
                                            <span className="inline-flex size-9 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
                                                <Sparkles size={17} aria-hidden="true" />
                                            </span>
                                            <h2 className="mt-4 text-[21px] font-medium leading-tight tracking-[-0.02em]">
                                                Let’s make something useful.
                                            </h2>
                                            <p className="mt-2 max-w-[38ch] text-[13.5px] leading-relaxed text-muted-foreground text-pretty">
                                                Describe the app you want. Build updates land here
                                                as they happen.
                                            </p>
                                        </div>
                                    )}
                                    {messages.map((message) => (
                                        <MessageBubble
                                            key={message.id}
                                            message={message}
                                            pills={pills}
                                            connected={connected}
                                            onWorkflowChanged={decided}
                                            canRespond={message.id === `run:${pendingDecisionId}`}
                                        />
                                    ))}
                                    {isBuilding &&
                                        !messages.some(
                                            (message) => message.id === `run:${runId}`,
                                        ) && (
                                            <div
                                                className="flex items-center gap-2.5 text-[12.5px] text-muted-foreground"
                                                role="status"
                                            >
                                                <ThinkingOrb
                                                    state="working"
                                                    size={20}
                                                    aria-hidden="true"
                                                />
                                                Working on your app. Stop it below any time.
                                            </div>
                                        )}
                                </div>
                            </div>
                            <ChatInput
                                projectId={chatId}
                                projectSkills={projectSkills}
                                onManage={(tab) => {
                                    setShowPreview(true);
                                    setMobilePane("preview");
                                    setPreviewTab(tab);
                                }}
                                files={projectFiles}
                                input={input}
                                connected={connected}
                                isBuilding={isBuilding}
                                onInputChange={setInput}
                                onSubmit={handleSendMessage}
                                onCancel={handleCancel}
                                canCancel={Boolean(runId)}
                                awaitingInput={awaitingInput}
                                pendingKind={pendingKind}
                                mode={mode}
                                onModeChange={setMode}
                                models={models}
                                modelChoice={modelChoice}
                                onModelChoiceChange={setModelChoice}
                            />
                        </section>
                        {showPreview && (
                            <>
                                <div
                                    hidden={chatHidden}
                                    className="relative z-10 w-px shrink-0 cursor-col-resize touch-none bg-border outline-offset-0 [transition:background-color_140ms_ease] before:absolute before:inset-y-0 before:-inset-x-1 before:content-[''] focus-visible:bg-ring focus-visible:outline-none [[data-resizing]_&]:bg-ring pointer-fine:hover:bg-ring max-md:hidden"
                                    role="separator"
                                    aria-label="Resize conversation and preview"
                                    aria-orientation="vertical"
                                    aria-valuenow={100 - previewWidth}
                                    aria-valuemin={20}
                                    aria-valuemax={70}
                                    tabIndex={0}
                                    {...resizeHandlers}
                                    onKeyDown={(event) => {
                                        if (
                                            event.key === "ArrowLeft" ||
                                            event.key === "ArrowRight"
                                        ) {
                                            event.preventDefault();
                                            setPreviewWidth((width) =>
                                                Math.max(
                                                    30,
                                                    Math.min(
                                                        80,
                                                        width +
                                                            (event.key === "ArrowLeft" ? 5 : -5),
                                                    ),
                                                ),
                                            );
                                        }
                                    }}
                                />
                                <PreviewPanel
                                    appUrl={appUrl}
                                    previewWidth={chatHidden ? 100 : previewWidth}
                                    files={projectFiles}
                                    revisionId={revisionId}
                                    isBuilding={isBuilding}
                                    projectId={chatId}
                                    activeTab={previewTab}
                                    visible={workspaceVisible}
                                    onTabChange={setPreviewTab}
                                    openedFile={openedFile}
                                    phase={preview.phase}
                                    previewError={preview.error}
                                    onRetry={preview.retry}
                                    chatHidden={chatHidden}
                                    onToggleChat={() => setChatHidden(!chatHidden)}
                                    projectSkills={projectSkills}
                                />
                            </>
                        )}
                    </main>
                </div>
            </div>
        </OpenFileContext>
    );
}
