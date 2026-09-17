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
            className="ember-preview min-w-0 min-h-0 flex flex-col bg-muted [&[data-viewport=tablet]_iframe]:max-w-192 [&[data-viewport=mobile]_iframe]:max-w-[375px]"
            aria-label="App workspace"
            data-viewport={viewport}
            style={{ width: `${previewWidth}%` }}
        >
            <div className="ember-preview-toolbar min-h-12 border-b border-b-border flex items-center justify-between gap-2 py-[5px] px-3 bg-card [&>.ember-row]:gap-[3px] max-md:p-1.5 max-md:[&_.ember-icon]:w-7 max-md:[&_.ember-tab]:p-2 flex-wrap [&_.ember-row]:min-w-0">
                <div
                    className="ember-row flex items-center gap-3.5"
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
                <div className="ember-row flex items-center gap-3.5">
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
                    className="ember-preview-stage flex-1 min-h-0 overflow-auto flex justify-center p-5 [&_iframe]:h-full [&_iframe]:w-full [&_iframe]:min-h-70 [&_iframe]:border [&_iframe]:border-border [&_iframe]:rounded-[8px] [&_iframe]:bg-white [&>.ember-empty]:w-full [&>.ember-empty]:border-solid [&>.ember-empty]:justify-center max-md:p-2.5"
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
                        <div className="ember-empty py-17.5 px-[25px] flex flex-col items-center text-center gap-4 border border-dashed border-border rounded-[14px] text-muted-foreground [&_h2]:text-[22px] [&_h2]:text-foreground [&_p]:text-[14px] [&_p]:max-w-92.5">
                            <Eye size={34} />
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
            <div className="ember-preview-caption border-t border-t-border text-[10px] leading-[1.5] text-muted-foreground py-2 px-3.5">
                {activeTab === "preview"
                    ? "Live app preview · Source available in Files"
                    : "Saved source and assets · App databases need their own backups"}
            </div>
        </section>
    );
}
