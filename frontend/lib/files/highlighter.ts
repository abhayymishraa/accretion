import type { Monaco } from "@monaco-editor/react";
import type { ThemeRegistration } from "shiki/core";

/** The viewer's themes: Accretion dark and light, picked by the app's own mode. */
export const CODE_THEMES = { dark: "accretion-dark", light: "accretion-light" } as const;

// GitHub's token colours on the app's surfaces, with keywords in Accretion blue.
function accretion(
    base: ThemeRegistration,
    name: string,
    background: string,
    foreground: string,
    keyword: string,
) {
    return {
        ...base,
        name,
        colors: {
            ...base.colors,
            "editor.background": background,
            "editor.foreground": foreground,
        },
        tokenColors: [
            ...(base.tokenColors ?? []),
            {
                scope: ["keyword", "storage", "storage.type", "keyword.control"],
                settings: { foreground: keyword },
            },
        ],
    };
}

let installed: Promise<void> | null = null;

/**
 * Hands Monaco's colouring to Shiki so the viewer uses the Accretion themes above.
 * Loaded on first use and installed once per page.
 */
export function installShiki(monaco: Monaco): Promise<void> {
    installed ??= (async () => {
        const [
            { createHighlighterCore },
            { createJavaScriptRegexEngine },
            { shikiToMonaco },
            dark,
            light,
        ] = await Promise.all([
            import("shiki/core"),
            import("shiki/engine/javascript"),
            import("@shikijs/monaco"),
            import("@shikijs/themes/github-dark-default"),
            import("@shikijs/themes/github-light-default"),
        ]);
        const highlighter = await createHighlighterCore({
            themes: [
                accretion(dark.default, CODE_THEMES.dark, "#111214", "#e6e9ec", "#4cb3f5"),
                accretion(light.default, CODE_THEMES.light, "#ffffff", "#1c2127", "#1676c4"),
            ],
            // One per language getLanguageFromPath returns; shellscript also answers to "shell".
            langs: [
                import("@shikijs/langs/typescript"),
                import("@shikijs/langs/tsx"),
                import("@shikijs/langs/javascript"),
                import("@shikijs/langs/jsx"),
                import("@shikijs/langs/json"),
                import("@shikijs/langs/html"),
                import("@shikijs/langs/css"),
                import("@shikijs/langs/scss"),
                import("@shikijs/langs/python"),
                import("@shikijs/langs/markdown"),
                import("@shikijs/langs/yaml"),
                import("@shikijs/langs/xml"),
                import("@shikijs/langs/shellscript"),
            ],
            engine: createJavaScriptRegexEngine(),
        });
        // Monaco has no tsx or jsx language; shikiToMonaco only colours languages it knows.
        for (const id of ["tsx", "jsx"]) monaco.languages.register({ id });
        shikiToMonaco(highlighter, monaco);
    })();
    return installed;
}
