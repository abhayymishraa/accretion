"use client";

import { fileService } from "@/services/service.files";
import { useState } from "react";
import { toast } from "sonner";

export function downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

/** The whole project as a ZIP, shared by the Code tab and the panel's ••• menu. */
export function useProjectDownload(projectId: string, revisionId?: string | null) {
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadError, setDownloadError] = useState("");
    const revisionQuery = revisionId ? `revision_id=${encodeURIComponent(revisionId)}` : "";

    const handleDownloadAll = async () => {
        setIsDownloading(true);
        setDownloadError("");
        try {
            const blob = await fileService.downloadProject(projectId, revisionQuery);

            downloadBlob(blob, `${projectId}-files.zip`);
            toast.success("Project ZIP download started", {
                id: `download-${projectId}`,
            });
            return true;
        } catch {
            setDownloadError("Could not download the project ZIP. Please try again.");
            return false;
        } finally {
            setIsDownloading(false);
        }
    };

    return { isDownloading, downloadError, setDownloadError, handleDownloadAll };
}
