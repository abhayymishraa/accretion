"use client";

import { useCallback, useEffect, useRef, useState, type PointerEvent } from "react";

// A new object per click, so the viewer selects the file again even when the path repeats.
export type OpenedFile = { path: string };
// The workspace panel's tabs: the app preview, its files (Code), its skills and its connectors.
export type WorkspaceTab = "preview" | "files" | "skills" | "connectors" | "secrets";

export function useWorkspaceLayout() {
    const containerRef = useRef<HTMLElement>(null);
    const [previewWidth, setPreviewWidth] = useState(50);
    const [showPreview, setShowPreview] = useState(true);
    const [mobilePane, setMobilePane] = useState("chat");
    const [previewTab, setPreviewTab] = useState<WorkspaceTab>("preview");
    const [openedFile, setOpenedFile] = useState<OpenedFile | null>(null);
    const [desktopPreview, setDesktopPreview] = useState<boolean | null>(null);
    const workspaceVisible =
        showPreview && desktopPreview !== null && (desktopPreview || mobilePane === "preview");
    useEffect(() => {
        // Match the stylesheet's breakpoint, including CSS-hidden mobile chat.
        const media = window.matchMedia("(min-width: 768px)");
        const update = () => setDesktopPreview(media.matches);
        update();
        media.addEventListener("change", update);
        return () => media.removeEventListener("change", update);
    }, []);

    // Pointer capture tracks the drag; the iframe still takes moves from a captured pointer, so
    // data-resizing switches it off synchronously, before the first move over it.
    const resizeHandlers = {
        onPointerDown: (event: PointerEvent<HTMLElement>) => {
            if (event.button !== 0) return;
            event.preventDefault();
            event.currentTarget.setPointerCapture(event.pointerId);
            document.body.style.userSelect = "none";
            containerRef.current?.setAttribute("data-resizing", "");
        },
        onPointerMove: (event: PointerEvent<HTMLElement>) => {
            if (!event.currentTarget.hasPointerCapture(event.pointerId) || !containerRef.current)
                return;
            const rect = containerRef.current.getBoundingClientRect();
            const chatWidth = ((event.clientX - rect.left) / rect.width) * 100;
            // Held at the limits rather than ignored past them, so the edge never sticks short.
            setPreviewWidth(100 - Math.min(70, Math.max(20, chatWidth)));
        },
        onPointerUp: endResize,
        onPointerCancel: endResize,
    };
    function endResize() {
        document.body.style.userSelect = "";
        containerRef.current?.removeAttribute("data-resizing");
    }

    const openFile = useCallback((path: string) => {
        setShowPreview(true);
        setPreviewTab("files");
        setMobilePane("preview");
        setOpenedFile({ path });
    }, []);

    return {
        openedFile,
        openFile,
        previewWidth,
        setPreviewWidth,
        resizeHandlers,
        showPreview,
        setShowPreview,
        mobilePane,
        setMobilePane,
        previewTab,
        setPreviewTab,
        workspaceVisible,
        containerRef,
    };
}
