"use client";

import { useRef, useSyncExternalStore, type KeyboardEvent, type PointerEvent } from "react";

const COLLAPSED_KEY = "accretion-sidebar";
const WIDTH_KEY = "accretion-sidebar-width";
const CHANGED = "accretion-sidebar-changed";
// Open WebUI clamps its sidebar to 220-480px; ours runs narrower, matching its 212px default.
export const SIDEBAR_WIDTH = { min: 200, max: 400, initial: 212, rail: 56 };
// Dragged narrower than this, the sidebar folds to its icon strip instead of stopping at min.
const FOLD_BELOW = 120;
// Where storage is blocked (private mode) the choices live here for this tab.
const fallback: { collapsed?: boolean; width?: number } = {};

function subscribe(onChange: () => void) {
    window.addEventListener(CHANGED, onChange);
    window.addEventListener("storage", onChange);
    return () => {
        window.removeEventListener(CHANGED, onChange);
        window.removeEventListener("storage", onChange);
    };
}

function readStored(key: string) {
    try {
        return localStorage.getItem(key);
    } catch {
        return null;
    }
}

function readCollapsed() {
    return fallback.collapsed ?? readStored(COLLAPSED_KEY) === "collapsed";
}

function readWidth() {
    const width = fallback.width ?? Number(readStored(WIDTH_KEY));
    return width >= SIDEBAR_WIDTH.min && width <= SIDEBAR_WIDTH.max ? width : SIDEBAR_WIDTH.initial;
}

function store(key: string, value: string, remember: () => void) {
    try {
        localStorage.setItem(key, value);
    } catch {
        remember();
    }
    window.dispatchEvent(new Event(CHANGED));
}

const clamp = (width: number) =>
    Math.min(SIDEBAR_WIDTH.max, Math.max(SIDEBAR_WIDTH.min, Math.round(width)));

/** The sidebar's folded state and width, remembered across pages and visits. */
export function useSidebarLayout() {
    const collapsed = useSyncExternalStore(subscribe, readCollapsed, () => false);
    const width = useSyncExternalStore(subscribe, readWidth, () => SIDEBAR_WIDTH.initial);
    const setCollapsed = (next: boolean) =>
        store(COLLAPSED_KEY, next ? "collapsed" : "expanded", () => (fallback.collapsed = next));
    const setWidth = (next: number) =>
        store(WIDTH_KEY, String(clamp(next)), () => (fallback.width = clamp(next)));
    return { collapsed, setCollapsed, width, setWidth };
}

type Layout = ReturnType<typeof useSidebarLayout>;

/**
 * Drag-to-resize for the sidebar's edge, after Open WebUI's Sidebar.svelte (open-webui/open-webui@8bd8b4f):
 * pointer capture keeps the drag alive off the handle, and the width rides a CSS variable until release.
 */
export function useSidebarResize(sidebar: React.RefObject<HTMLElement | null>, layout: Layout) {
    const drag = useRef<{ x: number; start: number; width: number } | null>(null);
    const end = () => {
        if (!drag.current) return;
        if (!layout.collapsed) layout.setWidth(drag.current.width);
        drag.current = null;
        delete sidebar.current?.dataset.resizing;
        document.body.style.userSelect = "";
    };
    return {
        onPointerDown: (event: PointerEvent<HTMLElement>) => {
            if (event.button !== 0) return;
            event.preventDefault();
            event.currentTarget.setPointerCapture(event.pointerId);
            const start = layout.collapsed ? SIDEBAR_WIDTH.rail : layout.width;
            drag.current = { x: event.clientX, start, width: layout.width };
            if (sidebar.current) sidebar.current.dataset.resizing = "";
            document.body.style.userSelect = "none";
        },
        onPointerMove: (event: PointerEvent<HTMLElement>) => {
            if (!drag.current) return;
            const raw = drag.current.start + event.clientX - drag.current.x;
            const fold = raw < FOLD_BELOW;
            if (fold !== layout.collapsed) layout.setCollapsed(fold);
            if (fold) return;
            drag.current.width = clamp(raw);
            sidebar.current?.style.setProperty("--sidebar-width", `${drag.current.width}px`);
        },
        onPointerUp: end,
        onPointerCancel: end,
        onDoubleClick: () => {
            layout.setCollapsed(false);
            layout.setWidth(SIDEBAR_WIDTH.initial);
        },
        onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
            if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
            event.preventDefault();
            const step = event.key === "ArrowRight" ? 16 : -16;
            if (layout.collapsed) return step > 0 && layout.setCollapsed(false);
            if (layout.width + step < SIDEBAR_WIDTH.min) return layout.setCollapsed(true);
            layout.setWidth(layout.width + step);
        },
    };
}
