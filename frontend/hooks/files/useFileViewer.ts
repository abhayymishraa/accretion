"use client";

import { fileService } from "@/services/service.files";
import type { OpenedFile } from "@/hooks/chat/useWorkspaceLayout";

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

function downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
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
    const [fileContent, setFileContent] = useState<string>("");
    const [isLoadingFile, setIsLoadingFile] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadError, setDownloadError] = useState("");
    const [binary, setBinary] = useState(false);
    const revisionQuery = revisionId ? `revision_id=${encodeURIComponent(revisionId)}` : "";

    useEffect(() => {
        if (!selectedFile) return;
        const sessionId = getSessionId();
        const key =
            sessionId && revisionId
                ? JSON.stringify([sessionId, projectId, revisionId, selectedFile])
                : null;
        const cached = key ? getCachedFile(key) : undefined;
        if (cached) {
            setBinary(cached.binary);
            setFileContent(cached.content ?? "");
            setIsLoadingFile(false);
            return;
        }
        const controller = new AbortController();
        setIsLoadingFile(true);
        setBinary(false);
        setFileContent("");
        fileService
            .read(projectId, selectedFile, revisionQuery, controller.signal)
            .then((data) => {
                if (controller.signal.aborted || getSessionId() !== sessionId) return;
                if (key) cacheFile(key, data);
                setBinary(data.binary);
                setFileContent(data.content ?? "");
            })
            .catch(() => {
                if (!controller.signal.aborted)
                    setFileContent("Saved file could not be loaded. Try again.");
            })
            .finally(() => {
                if (!controller.signal.aborted) setIsLoadingFile(false);
            });
        return () => controller.abort();
    }, [projectId, selectedFile, revisionId, revisionQuery]);

    const handleDownloadFile = async () => {
        if (!selectedFile) return;
        setDownloadError("");
        try {
            const blob = await fileService.downloadFile(projectId, selectedFile, revisionQuery);
            downloadBlob(blob, selectedFile.split("/").pop() || "file.txt");
            toast.success("File download started", {
                description: selectedFile,
                id: `download-${projectId}`,
            });
        } catch {
            setDownloadError("Could not download this file. Please try again.");
        }
    };

    const handleDownloadAll = async () => {
        setIsDownloading(true);
        setDownloadError("");
        try {
            const blob = await fileService.downloadProject(projectId, revisionQuery);

            downloadBlob(blob, `${projectId}-files.zip`);
            toast.success("Project ZIP download started", {
                id: `download-${projectId}`,
            });
        } catch {
            setDownloadError("Could not download the project ZIP. Please try again.");
        } finally {
            setIsDownloading(false);
        }
    };

    // Auto-select first file
    useEffect(() => {
        if (!files.length) {
            setSelectedFile(null);
            return;
        }
        if (!selectedFile || !files.includes(selectedFile)) {
            const firstFile = files.find((f) => !f.includes("/")) || files[0];
            setSelectedFile(firstFile);
        }
    }, [files, selectedFile]);

    return {
        selectedFile,
        setSelectedFile,
        fileContent,
        isLoadingFile,
        isDownloading,
        downloadError,
        binary,
        handleDownloadFile,
        handleDownloadAll,
    };
}
