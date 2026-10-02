"use client";

import { fileService } from "@/services/service.files";
import type { OpenedFile } from "@/hooks/chat/useWorkspaceLayout";
import { downloadBlob } from "@/hooks/files/useProjectDownload";

import { getSessionId } from "@/lib/auth/session";
import { cacheFile, getCachedFile } from "@/lib/files/contentCache";
import { useEffect, useState } from "react";
import { toast } from "sonner";

interface FileViewerProps {
    files: string[];
    projectId: string;
    revisionId?: string | null;
    openedFile?: OpenedFile | null;
}

export function useFileViewer({ files, projectId, revisionId, openedFile }: FileViewerProps) {
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    // A file opened from the run timeline. Adjusted during render, not in an effect, so the
    // viewer never paints the previous file first; null start lets a freshly mounted viewer apply it.
    const [handled, setHandled] = useState<OpenedFile | null>(null);
    if (openedFile && openedFile !== handled) {
        setHandled(openedFile);
        if (files.includes(openedFile.path)) setSelectedFile(openedFile.path);
    }
    const [downloadError, setDownloadError] = useState("");
    const revisionQuery = revisionId ? `revision_id=${encodeURIComponent(revisionId)}` : "";
    // Derived, not synced in an effect: a missing or vanished selection falls back to the first file.
    const current =
        selectedFile && files.includes(selectedFile)
            ? selectedFile
            : (files.find((f) => !f.includes("/")) ?? files[0] ?? null);
    const loadKey = JSON.stringify([projectId, revisionId, current]);
    const [loaded, setLoaded] = useState<{ key: string; content: string; binary: boolean }>();
    const isLoadingFile = Boolean(current) && loaded?.key !== loadKey;

    useEffect(() => {
        if (!current) return;
        const sessionId = getSessionId();
        const key =
            sessionId && revisionId
                ? JSON.stringify([sessionId, projectId, revisionId, current])
                : null;
        const cached = key ? getCachedFile(key) : undefined;
        const controller = new AbortController();
        (cached
            ? Promise.resolve(cached)
            : fileService.read(projectId, current, revisionQuery, controller.signal)
        )
            .then((data) => {
                if (controller.signal.aborted || getSessionId() !== sessionId) return;
                if (key && !cached) cacheFile(key, data);
                setLoaded({ key: loadKey, content: data.content ?? "", binary: data.binary });
            })
            .catch(() => {
                if (!controller.signal.aborted)
                    setLoaded({
                        key: loadKey,
                        content: "Saved file could not be loaded. Try again.",
                        binary: false,
                    });
            });
        return () => controller.abort();
    }, [projectId, current, revisionId, revisionQuery, loadKey]);

    const handleDownloadFile = async () => {
        if (!current) return;
        setDownloadError("");
        try {
            const blob = await fileService.downloadFile(projectId, current, revisionQuery);
            downloadBlob(blob, current.split("/").pop() || "file.txt");
            toast.success("File download started", {
                description: current,
                id: `download-${projectId}`,
            });
        } catch {
            setDownloadError("Could not download this file. Please try again.");
        }
    };

    return {
        selectedFile: current,
        setSelectedFile,
        fileContent: isLoadingFile ? "" : (loaded?.content ?? ""),
        isLoadingFile,
        downloadError,
        binary: !isLoadingFile && Boolean(loaded?.binary),
        handleDownloadFile,
    };
}
