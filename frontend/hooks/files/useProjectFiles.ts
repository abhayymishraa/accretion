"use client";

import { fileService } from "@/services/service.files";

import { useEffect, useRef, useState } from "react";

export function useProjectFiles(chatId: string, isBuilding: boolean) {
    const [projectFiles, setProjectFiles] = useState<string[]>([]);
    const [revisionId, setRevisionId] = useState<string | null>(null);
    // A build starting changes no files yet: only a new project or a build ending loads at once.
    // `loadedChat` is the chat whose list has loaded or is loading; `latestRequest` lets only the
    // newest load apply, so a build starting mid-load keeps that load instead of repeating it.
    const loadedChat = useRef<string | null>(null);
    const latestRequest = useRef(0);
    // Saved files stay accessible after the sandbox expires. Poll metadata only during a run.
    useEffect(() => {
        if (!chatId) return;
        const loadFiles = async () => {
            const request = ++latestRequest.current;
            loadedChat.current = chatId;
            try {
                const data = await fileService.list(chatId);
                if (request === latestRequest.current) {
                    setProjectFiles(data.files);
                    setRevisionId(data.revision_id);
                }
            } catch {
                // Keep the last readable checkpoint during a temporary outage; the next run of
                // this effect loads at once instead of waiting for a poll.
                if (request === latestRequest.current) loadedChat.current = null;
            }
        };
        if (!isBuilding || loadedChat.current !== chatId) void loadFiles();
        const timer = isBuilding
            ? setInterval(() => {
                  void loadFiles();
              }, 10000)
            : undefined;
        return () => {
            if (timer) clearInterval(timer);
        };
    }, [chatId, isBuilding]);

    return { projectFiles, revisionId };
}
