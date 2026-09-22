"use client";

import { Button } from "@/components/ui/button";

import { ChatIdHeader } from "@/components/chat/ChatIdHeader";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { PreviewPanel } from "@/components/chat/PreviewPanel";
import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { Loader2, Sparkles } from "lucide-react";

import { useChatWorkspace } from "@/hooks/chat/useChatWorkspace";
export default function ChatWorkspace({ chatId }: { chatId: string }) {
    const {
        router,
        wsConnected,
        messages,
        error,
        input,
        setInput,
        mode,
        setMode,
        awaitingInput,
        pendingDecisionId,
        isLoading,
        hasOlder,
        loadingOlder,
        loadOlder,
        refreshHistory,
        appUrl,
        revisionId,
        isBuilding,
        runId,
        previewWidth,
        setPreviewWidth,
        setIsDragging,
        showPreview,
        setShowPreview,
        userData,
        mobilePane,
        setMobilePane,
        projectFiles,
        previewTab,
        setPreviewTab,
        workspaceVisible,
        preview,
        handleConversationScroll,
        trackRef,
        conversationRef,
        containerRef,
        handleSendMessage,
        handleCancel,
    } = useChatWorkspace(chatId);
    return (
        <div className="ember-builder flex h-dvh min-h-0 flex-col overflow-hidden bg-background">
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
                className="ember-mobile-tabs hidden max-md:flex max-md:gap-1 max-md:border-b max-md:border-b-border max-md:px-3 max-md:py-1.5 max-md:[&>button]:flex-1"
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
            <div className="ember-builder-shell flex min-h-0 flex-1 max-[1101px]:[&>.ember-workspace-sidebar]:hidden">
                <WorkspaceSidebar current="builder" />
                <main
                    ref={containerRef}
                    className="ember-builder-body flex min-h-0 flex-1 gap-px overflow-hidden bg-border max-md:gap-0 max-md:[&[data-mobile-pane=chat]>.ember-preview]:hidden max-md:[&[data-mobile-pane=preview]>.ember-conversation]:hidden max-md:[&>.ember-preview]:w-full! max-md:[&>.ember-conversation]:w-full!"
                    data-mobile-pane={mobilePane}
                    id="main-content"
                >
                    <section
                        className="ember-conversation flex min-h-0 min-w-0 flex-col bg-surface-1"
                        aria-label="Project conversation"
                        style={{ width: showPreview ? `${100 - previewWidth}%` : "100%" }}
                    >
                        <div
                            className="ember-message-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-8 [overflow-anchor:none] max-md:px-4 max-md:py-5"
                            ref={conversationRef}
                            onScroll={handleConversationScroll}
                        >
                            <div
                                className="mx-auto flex w-full max-w-[46rem] flex-col gap-7"
                                ref={trackRef}
                            >
                                {isLoading && (
                                    <div
                                        className="flex items-center gap-2.5 text-[12.5px] text-muted-foreground"
                                        role="status"
                                    >
                                        <Loader2 size={15} className="animate-spin" />
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
                                        {loadingOlder ? "Loading older messages…" : "Show earlier"}
                                    </Button>
                                )}
                                {error && (
                                    <p
                                        className="flex flex-wrap items-center gap-2 rounded-[10px] border border-destructive/40 bg-destructive/10 px-4 py-3 text-[13px] leading-relaxed text-destructive"
                                        role="alert"
                                    >
                                        {error}
                                        <Button
                                            variant="utility"
                                            className="text-destructive"
                                            onClick={refreshHistory}
                                        >
                                            Retry
                                        </Button>
                                    </p>
                                )}
                                {!messages.length && !isLoading && !error && (
                                    <div className="ember-chat-intro pt-2 pb-4">
                                        <span className="inline-flex size-9 items-center justify-center rounded-[10px] bg-accent text-accent-foreground">
                                            <Sparkles size={17} aria-hidden="true" />
                                        </span>
                                        <h2 className="mt-4 text-[21px] font-medium leading-tight tracking-[-0.02em]">
                                            Let’s make something useful.
                                        </h2>
                                        <p className="mt-2 max-w-[38ch] text-[13.5px] leading-relaxed text-muted-foreground text-pretty">
                                            Describe the app you want. Build updates land here as
                                            they happen.
                                        </p>
                                    </div>
                                )}
                                {messages.map((message) => (
                                    <MessageBubble
                                        key={message.id}
                                        message={message}
                                        connected={wsConnected}
                                        onWorkflowChanged={refreshHistory}
                                        canRespond={message.id === `run:${pendingDecisionId}`}
                                    />
                                ))}
                                {isBuilding &&
                                    !messages.some((message) => message.id === `run:${runId}`) && (
                                        <div
                                            className="flex items-center gap-2.5 text-[12.5px] text-muted-foreground"
                                            role="status"
                                        >
                                            <Loader2 size={14} className="animate-spin" />
                                            Working on your app. Stop it below any time.
                                        </div>
                                    )}
                            </div>
                        </div>
                        <ChatInput
                            files={projectFiles}
                            input={input}
                            wsConnected={wsConnected}
                            isBuilding={isBuilding}
                            onInputChange={setInput}
                            onSubmit={handleSendMessage}
                            onCancel={handleCancel}
                            canCancel={Boolean(runId)}
                            awaitingInput={awaitingInput}
                            mode={mode}
                            onModeChange={setMode}
                        />
                    </section>
                    {showPreview && (
                        <>
                            <div
                                className="ember-resizer w-px shrink-0 cursor-col-resize touch-none bg-border outline-offset-0 [transition:background-color_140ms_ease] focus-visible:bg-ring focus-visible:outline-none pointer-fine:hover:bg-ring max-md:hidden"
                                role="separator"
                                aria-label="Resize conversation and preview"
                                aria-orientation="vertical"
                                aria-valuenow={100 - previewWidth}
                                aria-valuemin={20}
                                aria-valuemax={70}
                                tabIndex={0}
                                onMouseDown={() => setIsDragging(true)}
                                onKeyDown={(event) => {
                                    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                                        event.preventDefault();
                                        setPreviewWidth((width) =>
                                            Math.max(
                                                30,
                                                Math.min(
                                                    80,
                                                    width + (event.key === "ArrowLeft" ? 5 : -5),
                                                ),
                                            ),
                                        );
                                    }
                                }}
                            />
                            <PreviewPanel
                                appUrl={appUrl}
                                previewWidth={previewWidth}
                                files={projectFiles}
                                revisionId={revisionId}
                                isBuilding={isBuilding}
                                projectId={chatId}
                                activeTab={previewTab}
                                visible={workspaceVisible}
                                onTabChange={setPreviewTab}
                                phase={preview.phase}
                                previewError={preview.error}
                                onRetry={preview.retry}
                            />
                        </>
                    )}
                </main>
            </div>
        </div>
    );
}
