"use client";

import { Button } from "@/components/ui/button";

import { ChatIdHeader } from "@/components/chat/ChatIdHeader";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { PreviewPanel } from "@/components/chat/PreviewPanel";
import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { Code2, Loader2 } from "lucide-react";

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
        messagesEndRef,
        conversationRef,
        containerRef,
        handleSendMessage,
        handleCancel,
    } = useChatWorkspace(chatId);
    return (
        <div className="ember-builder h-dvh min-h-125 flex flex-col overflow-hidden bg-background max-md:min-h-112.5 max-md:[&_.ember-workspace-header>.ember-row]:gap-0.5 max-md:[&_.ember-workspace-header_.ember-icon]:w-7.5 transcript-workspace [&.ember-builder]:min-h-0">
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
                className="ember-mobile-tabs hidden max-md:flex max-md:gap-1.5 max-md:py-[7px] max-md:px-[15px] max-md:border-b max-md:border-b-border max-md:[&>button]:flex-1"
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
            <div className="ember-builder-shell flex flex-1 min-h-0 max-[1101px]:[&>.ember-workspace-sidebar]:hidden">
                <WorkspaceSidebar current="builder" />
                <main
                    ref={containerRef}
                    className="ember-builder-body flex-1 min-h-0 flex overflow-hidden max-md:[&[data-mobile-pane=chat]>.ember-preview]:hidden max-md:[&[data-mobile-pane=preview]>.ember-conversation]:hidden max-md:[&>.ember-preview]:w-full! max-md:[&>.ember-conversation]:w-full!"
                    data-mobile-pane={mobilePane}
                    id="main-content"
                >
                    <section
                        className="ember-conversation flex flex-col min-w-0 min-h-0 bg-card"
                        aria-label="Project conversation"
                        style={{ width: showPreview ? `${100 - previewWidth}%` : "100%" }}
                    >
                        <div className="ember-conversation-toolbar min-h-12 flex items-center justify-between gap-2.5 py-1.5 px-3.5 border-b border-b-border [&_.ember-row]:gap-[5px] [&_button]:text-[12px]">
                            <span className="ember-helper text-[12px] leading-[1.6] text-muted-foreground">
                                Conversation
                            </span>
                        </div>
                        <div
                            className="ember-message-scroll flex-1 min-h-0 overflow-y-auto overscroll-contain py-[25px] px-6 flex flex-col gap-[23px] max-md:py-5 max-md:px-4"
                            ref={conversationRef}
                            onScroll={handleConversationScroll}
                        >
                            {isLoading && (
                                <div
                                    className="ember-row flex items-center gap-3.5 ember-helper text-[12px] leading-[1.6] text-muted-foreground"
                                    role="status"
                                >
                                    <Loader2 size={18} className="animate-spin" />
                                    Loading messages…
                                </div>
                            )}
                            {hasOlder && (
                                <Button
                                    variant="utility"
                                    disabled={loadingOlder}
                                    onClick={loadOlder}
                                >
                                    {loadingOlder
                                        ? "Loading older messages…"
                                        : "Load older messages"}
                                </Button>
                            )}
                            {error && (
                                <p
                                    className="ember-error text-destructive border border-destructive bg-card py-3 px-[15px] rounded-[8px] text-[13px] leading-[1.5]"
                                    role="alert"
                                >
                                    {error}
                                    <Button variant="utility" onClick={refreshHistory}>
                                        Retry
                                    </Button>
                                </p>
                            )}
                            {!messages.length && !isLoading && !error && (
                                <div className="ember-chat-intro pt-3 px-0 pb-5 [&>svg]:text-accent-foreground [&>svg]:mb-4.5 [&_h2]:text-[23px] [&_h2]:leading-[1.2] [&_h2]:tracking-[-0.7px] [&_h2]:font-medium [&_p]:text-muted-foreground [&_p]:text-[13px] [&_p]:leading-[1.7] [&_p]:mt-2.5">
                                    <Code2 size={26} />
                                    <h2>Let’s make something useful.</h2>
                                    <p>Your conversation and build updates will appear here.</p>
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
                                        className="ember-row flex items-center gap-3.5 ember-helper text-[12px] leading-[1.6] text-muted-foreground"
                                        role="status"
                                    >
                                        <Loader2 size={15} className="animate-spin" />
                                        Working on your app. You can stop this run below.
                                    </div>
                                )}
                            <div ref={messagesEndRef} />
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
                                className="ember-resizer w-[5px] shrink-0 bg-border cursor-col-resize touch-none focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-ring focus-visible:outline-offset-[-1px] hover:bg-ring max-md:hidden"
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
