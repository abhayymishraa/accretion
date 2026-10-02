"use client";

import { useLightTheme } from "@/components/layout/ThemeProvider";
import { CODE_THEMES, installShiki } from "@/lib/files/highlighter";
import { useMonaco } from "@monaco-editor/react";
import { useEffect, useState } from "react";

/** The editor theme for the app's current mode, once Shiki is installed in Monaco. */
export function useCodeTheme() {
    const monaco = useMonaco();
    const light = useLightTheme();
    const [state, setState] = useState<"loading" | "ready" | "failed">("loading");
    useEffect(() => {
        if (!monaco) return;
        installShiki(monaco).then(
            () => setState("ready"),
            // A chunk that fails to load keeps the code readable in Monaco's own themes.
            () => setState("failed"),
        );
    }, [monaco]);
    const theme =
        state === "failed" ? (light ? "vs" : "vs-dark") : CODE_THEMES[light ? "light" : "dark"];
    return { ready: state !== "loading", theme };
}
