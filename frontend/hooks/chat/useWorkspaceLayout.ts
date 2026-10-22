"use client";

import { returnProject, takeReturn } from "@/hooks/publish/usePublish";
import {
    useCallback,
    useEffect,
    useRef,
    useState,
    useSyncExternalStore,
    type PointerEvent,
} from "react";

// A new object per click, so the viewer selects the file again even when the path repeats.
export type OpenedFile = { path: string };
export type WorkspaceTab =
    | "preview"
    | "publish"
    | "files"
    | "skills"
    | "connectors"
    | "secrets"
    | "github"
    | "database"
    | "services";

// The return key is written before the page leaves for Vercel and read once on the way back: nothing to watch.
const unwatched = () => () => {};

export function useWorkspaceLayout(projectId: string) {
    const containerRef = useRef<HTMLElement>(null);
    const [previewWidth, setPreviewWidth] = useState(50);
    const [showPreview, setShowPreview] = useState(true);
    const [mobilePane, setMobilePane] = useState("chat");
    const [previewTab, setPreviewTab] = useState<WorkspaceTab>("preview");
    const [openedFile, setOpenedFile] = useState<OpenedFile | null>(null);
    const [desktopPreview, setDesktopPreview] = useState<boolean | null>(null);
    // Back from connecting Vercel: the Publish tab opens, once. Read after hydration, since the server has no
    // sessionStorage; an initial state would render a different tab on the server and the client.
    const returned = useSyncExternalStore(unwatched, returnProject, () => null) === projectId;
    const [landed, setLanded] = useState(false);
    if (returned && !landed) {
        setLanded(true);
        setShowPreview(true);
        setPreviewTab("publish");
        setMobilePane("preview");
    }
    useEffect(() => {
        if (returned) takeReturn(projectId);
    }, [returned, projectId]);
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
