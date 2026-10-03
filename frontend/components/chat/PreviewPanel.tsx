import { FileViewer } from "@/components/files/FileViewer";
import { EFFECTS } from "@/config/effects";
import dynamic from "next/dynamic";
import type { OpenedFile } from "@/hooks/chat/useWorkspaceLayout";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { TetrisLoader } from "@/components/ui/loader-tetris";
import type { PreviewPhase } from "@/types/preview.type";
import { Eye } from "lucide-react";
import { usePreviewHistory } from "@/hooks/preview/usePreviewHistory";
import { useEffect, useRef, useState } from "react";
import { PreviewAddressBar } from "./PreviewAddressBar";
import { PreviewToolbar } from "./PreviewToolbar";

interface PreviewPanelProps {
    appUrl: string | null;
    previewWidth: number;
    files: string[];
    projectId: string;
    revisionId?: string | null;
    isBuilding?: boolean;
    activeTab: TabType;
    visible: boolean;
    onTabChange: (tab: TabType) => void;
    phase: PreviewPhase;
    previewError: string | null;
    onRetry: () => void;
    openedFile: OpenedFile | null;
    chatHidden: boolean;
    onToggleChat: () => void;
}
// Loaded only when switched on: img-fx brings three.js with it.
const PreviewReveal = dynamic(() => import("@/components/effects/PreviewReveal"), { ssr: false });

type TabType = "preview" | "files";
// Decorative: the text beside it announces the state.
const BUILD_LOADER = <TetrisLoader aria-hidden rows={12} cellSize={3} gap={1} />;

export function PreviewPanel({
    appUrl,
    previewWidth,
    files,
    projectId,
    revisionId,
    isBuilding,
    activeTab,
    visible,
    onTabChange,
    phase,
    previewError,
    onRetry,
    openedFile,
    chatHidden,
    onToggleChat,
}: PreviewPanelProps) {
    const [mobile, setMobile] = useState(false);
    const [route, setRoute] = useState("/");
    const src = appUrl ? new URL(route, appUrl).href : null;
    const frame = useRef<HTMLIFrameElement>(null);
    const previewHistory = usePreviewHistory(frame, appUrl);
    const [refresh, setRefresh] = useState(0);
    const frameKey = `${projectId}-${refresh}`;
    // The frame that last painted; a refresh re-mounts it under a new key and shows the loader again.
    const [paintedKey, setPaintedKey] = useState<string | null>(null);
    const [retainPreview, setRetainPreview] = useState(false);
    const building = isBuilding || phase === "building";
    const live = Boolean(appUrl) && phase === "active" && !building;
    const previewReady = visible && live;
    // Reset before children render so a stale retention flag cannot mount an iframe.
    if (retainPreview && !previewReady) {
        setRetainPreview(false);
    } else if (!retainPreview && previewReady && activeTab === "preview") {
        setRetainPreview(true);
    }
    // An unmounted frame comes back unpainted, so its loader must show again.
    const frameMounted = visible && live && (activeTab === "preview" || retainPreview);
    if (!frameMounted && paintedKey !== null) setPaintedKey(null);
    useEffect(() => {
        if (!previewReady || activeTab === "preview") return;
        // A short Files visit preserves the iframe. Hidden work is bounded.
        const timer = setTimeout(() => setRetainPreview(false), 60_000);
        return () => clearTimeout(timer);
    }, [activeTab, previewReady, appUrl]);
    const preparing = phase === "checking" || phase === "opening";

    let emptyTitle = "Your canvas is ready.";
    if (building) {
        emptyTitle = "Building your app…";
    } else if (preparing) {
        emptyTitle = "Loading your app…";
    } else if (previewError) {
        emptyTitle = "Preview unavailable.";
    } else if (revisionId) {
        emptyTitle = "Your preview is sleeping.";
    }

    let emptyDescription = "The app preview will appear when your build makes it available.";
    if (building) {
        emptyDescription = "Follow the existing build in your conversation.";
    } else if (preparing) {
        emptyDescription = "Your saved project will appear here shortly.";
    } else if (revisionId) {
        emptyDescription = "Your saved files are available in Files.";
    }

    return (
        <section
            className="ember-preview min-w-0 min-h-0 flex flex-col bg-surface-1"
            aria-label="App workspace"
            style={{ width: `${previewWidth}%` }}
        >
            <PreviewToolbar
                activeTab={activeTab}
                onTabChange={onTabChange}
                chatHidden={chatHidden}
                onToggleChat={onToggleChat}
                projectId={projectId}
                revisionId={revisionId}
            />
            {activeTab === "preview" && (
                <PreviewAddressBar
                    src={src}
                    current={previewHistory.path}
                    canBack={previewHistory.canBack}
                    canForward={previewHistory.canForward}
                    onBack={previewHistory.back}
                    onForward={previewHistory.forward}
                    phase={phase}
                    mobile={mobile}
                    onToggleMobile={() => setMobile(!mobile)}
                    // Through the bridge when there is one, so even the frame's first path reloads.
                    onNavigate={(path) => previewHistory.visit(path) || setRoute(path)}
                    onRefresh={() =>
                        previewHistory.path
                            ? previewHistory.reload()
                            : setRefresh((value) => value + 1)
                    }
                />
            )}
            {visible && (activeTab === "preview" || retainPreview) && (
                // Every state fills the pane edge to edge under the address bar; only phone width is framed.
                <div
                    className={`ember-preview-stage relative flex min-h-0 flex-1 justify-center overflow-auto [&_iframe]:h-full [&_iframe]:w-full [&_iframe]:opacity-0 [&_iframe[data-loaded]]:opacity-100 [&_iframe]:min-h-70 [&_iframe]:bg-white [&>.ember-empty]:w-full [&>.ember-empty]:justify-center ${live && mobile ? "p-4 max-md:p-2 [&_iframe]:border [&_iframe]:border-border" : ""}`}
                    style={activeTab === "files" ? { display: "none" } : undefined}
                >
                    {live ? (
                        <>
                            <iframe
                                ref={frame}
                                key={frameKey}
                                // Shown once the app has painted, so dark theme never flashes the frame's
                                // white background; a refresh re-mounts it and fades in again.
                                onLoad={(event) => {
                                    event.currentTarget.dataset.loaded = "";
                                    setPaintedKey(frameKey);
                                }}
                                src={src ?? undefined}
                                // Mobile ↔ responsive resizes in place; max-width is the one property that
                                // narrows the frame without scaling its content, so it is the one animated.
                                className={`${mobile ? "max-w-[375px]" : "max-w-full"} [transition:opacity_200ms_var(--ease-out),max-width_300ms_var(--ease-in-out)] motion-reduce:[transition:opacity_120ms_var(--ease-out)]`}
                                title="App preview"
                                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                            />
                            {paintedKey !== frameKey && (
                                <div
                                    role="status"
                                    className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-3 font-brand text-[16px] font-semibold tracking-[-0.3px]"
                                >
                                    {BUILD_LOADER}
                                    Loading your app…
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="ember-empty flex flex-col items-center gap-3 px-6 py-16 text-center text-muted-foreground [&_h2]:font-brand [&_h2]:text-[16px] [&_h2]:font-semibold [&_h2]:tracking-[-0.3px] [&_h2]:text-foreground [&_p]:max-w-[42ch] [&_p]:text-[12.5px] [&_p]:leading-relaxed">
                            {EFFECTS.previewImageReveal && building ? (
                                <PreviewReveal images={[]} />
                            ) : building || preparing ? (
                                BUILD_LOADER
                            ) : (
                                <Eye size={26} className="text-muted-foreground/60" />
                            )}
                            <h2>{emptyTitle}</h2>
                            <p role={preparing || building ? "status" : undefined}>
                                {emptyDescription}
                            </p>
                            {(revisionId || previewError) && !preparing && !building && (
                                <Button variant="default" onClick={onRetry}>
                                    {previewError ? "Retry" : "Resume preview"}
                                </Button>
                            )}
                            <div className="[&>[data-error-box]]:text-left">
                                <ErrorBox message={!building && previewError ? previewError : ""} />
                            </div>
                        </div>
                    )}
                </div>
            )}
            {activeTab === "files" && (
                <div className="ember-preview-files flex-1 min-h-0 overflow-hidden">
                    <FileViewer
                        key={projectId}
                        files={files}
                        projectId={projectId}
                        revisionId={revisionId}
                        openedFile={openedFile}
                    />
                </div>
            )}
        </section>
    );
}
