import { FileViewer } from "@/components/files/FileViewer";
import { Button, buttonVariants } from "@/components/ui/button";
import type { PreviewPhase } from "@/types/preview.type";
import {
    ExternalLink,
    Eye,
    FileCode,
    Globe,
    Monitor,
    RotateCcw,
    Smartphone,
    Tablet,
} from "lucide-react";
import { useEffect, useState } from "react";

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
}
type TabType = "preview" | "files";

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
}: PreviewPanelProps) {
    const [viewport, setViewport] = useState("desktop");
    const [refresh, setRefresh] = useState(0);
    const [retainPreview, setRetainPreview] = useState(false);
    const previewReady = visible && Boolean(appUrl) && phase === "active" && !isBuilding;
    // Reset before children render so a stale retention flag cannot mount an iframe.
    if (retainPreview && !previewReady) {
        setRetainPreview(false);
    } else if (!retainPreview && previewReady && activeTab === "preview") {
        setRetainPreview(true);
    }
    useEffect(() => {
        if (!previewReady || activeTab === "preview") return;
        // A short Files visit preserves the iframe. Hidden work is bounded.
        const timer = setTimeout(() => setRetainPreview(false), 60_000);
        return () => clearTimeout(timer);
    }, [activeTab, previewReady, appUrl]);
    const preparing = phase === "checking" || phase === "opening";
    const building = isBuilding || phase === "building";

    let emptyTitle = "Your canvas is ready.";
    if (building) {
        emptyTitle = "Your app is building.";
    } else if (preparing) {
        emptyTitle = "Preparing your preview…";
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
            className="ember-preview min-w-0 min-h-0 flex flex-col bg-surface-1 [&[data-viewport=tablet]_iframe]:max-w-192 [&[data-viewport=mobile]_iframe]:max-w-[375px]"
            aria-label="App workspace"
            data-viewport={viewport}
            style={{ width: `${previewWidth}%` }}
        >
            <div className="ember-preview-toolbar flex h-11 shrink-0 flex-wrap items-center justify-between gap-2 border-b border-b-border bg-background px-2 max-md:px-1.5 [&_.ember-row]:min-w-0">
                <div
                    className="ember-row flex items-center gap-0.5"
                    role="group"
                    aria-label="Preview views"
                >
                    <Button
                        variant="tab"
                        aria-pressed={activeTab === "preview"}
                        onClick={() => onTabChange("preview")}
                    >
                        <Globe size={14} />
                        Preview
                    </Button>
                    <Button
                        variant="tab"
                        aria-pressed={activeTab === "files"}
                        onClick={() => onTabChange("files")}
                    >
                        <FileCode size={14} />
                        Files{files.length ? ` (${files.length})` : ""}
                    </Button>
                </div>
                <div className="ember-row flex items-center gap-0.5">
                    {activeTab === "preview" && (
                        <>
                            <Button
                                variant="icon"
                                aria-label="Desktop preview"
                                aria-pressed={viewport === "desktop"}
                                onClick={() => setViewport("desktop")}
                            >
                                <Monitor size={15} />
                            </Button>
                            <Button
                                variant="icon"
                                aria-label="Tablet preview"
                                aria-pressed={viewport === "tablet"}
                                onClick={() => setViewport("tablet")}
                            >
                                <Tablet size={15} />
                            </Button>
                            <Button
                                variant="icon"
                                aria-label="Mobile preview"
                                aria-pressed={viewport === "mobile"}
                                onClick={() => setViewport("mobile")}
                            >
                                <Smartphone size={15} />
                            </Button>
                            <Button
                                variant="icon"
                                disabled={!appUrl || phase !== "active"}
                                aria-label="Reload preview"
                                onClick={() => setRefresh((value) => value + 1)}
                            >
                                <RotateCcw size={14} />
                            </Button>
                        </>
                    )}
                    {appUrl && phase === "active" && (
                        <a
                            href={appUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={buttonVariants({ variant: "icon" })}
                            aria-label="Open preview in new tab"
                        >
                            <ExternalLink size={15} />
                        </a>
                    )}
                </div>
            </div>
            {visible && (activeTab === "preview" || retainPreview) && (
                <div
                    className="ember-preview-stage flex min-h-0 flex-1 justify-center overflow-auto p-4 [&_iframe]:h-full [&_iframe]:w-full [&_iframe]:min-h-70 [&_iframe]:rounded-[10px] [&_iframe]:border [&_iframe]:border-border [&_iframe]:bg-white [&>.ember-empty]:w-full [&>.ember-empty]:justify-center max-md:p-2"
                    style={activeTab === "files" ? { display: "none" } : undefined}
                >
                    {appUrl && phase === "active" && !building ? (
                        <iframe
                            key={`${projectId}-${refresh}`}
                            src={appUrl}
                            title="App preview"
                            sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                        />
                    ) : (
                        <div className="ember-empty flex flex-col items-center gap-3 rounded-[14px] border border-dashed border-border px-6 py-16 text-center text-muted-foreground [&_h2]:text-[19px] [&_h2]:font-medium [&_h2]:tracking-[-0.01em] [&_h2]:text-foreground [&_p]:max-w-[42ch] [&_p]:text-[13.5px] [&_p]:leading-relaxed">
                            <Eye size={26} className="text-muted-foreground/60" />
                            <h2>{emptyTitle}</h2>
                            <p role={preparing || building ? "status" : undefined}>
                                {emptyDescription}
                            </p>
                            {(revisionId || previewError) && !preparing && !building && (
                                <Button variant="default" onClick={onRetry}>
                                    {previewError ? "Retry" : "Resume preview"}
                                </Button>
                            )}
                            {previewError && !building && <p role="alert">{previewError}</p>}
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
                    />
                </div>
            )}
            <div className="ember-preview-caption shrink-0 border-t border-t-border px-3.5 py-2 text-[10.5px] leading-[1.5] text-muted-foreground">
                {activeTab === "preview"
                    ? "Live app preview · Source available in Files"
                    : "Saved source and assets · App databases need their own backups"}
            </div>
        </section>
    );
}
