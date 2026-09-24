"use client";

import { Button } from "@/components/ui/button";

import { migrateKey } from "@/lib/storage/migrateKey";
import { Moon, Sun } from "lucide-react";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useSyncExternalStore } from "react";

const ThemeContext = createContext({ light: false, toggle: () => {} });
const themeKey = "accretion-theme";
const themeChanged = "accretion-theme-changed";
const legacyThemeKey = "webbuilder-theme";
let migrated = false;
let fallbackLight: boolean | null = null;
// Light-only like their data-palette content; the toggle lives in the workspace.
const LIGHT_ONLY_ROUTES = new Set(["/", "/signin", "/signup", "/verify-email", "/auth/callback"]);

function getTheme() {
    if (fallbackLight !== null) return fallbackLight;
    try {
        // Runs once per tab; carries a pre-rename preference onto the new key.
        if (!migrated) {
            migrated = true;
            migrateKey(localStorage, themeKey, legacyThemeKey);
        }
        return localStorage.getItem(themeKey) === "light";
    } catch {
        return false;
    }
}

function subscribeTheme(notify: () => void) {
    const onStorage = (event: StorageEvent) => {
        if (event.key === themeKey || event.key === null) {
            fallbackLight = null;
            notify();
        }
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener(themeChanged, notify);
    return () => {
        window.removeEventListener("storage", onStorage);
        window.removeEventListener(themeChanged, notify);
    };
}

function getServerTheme() {
    return false;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const light = useSyncExternalStore(subscribeTheme, getTheme, getServerTheme);
    const pathname = usePathname();
    useEffect(() => {
        document.documentElement.dataset.theme =
            light || LIGHT_ONLY_ROUTES.has(pathname) ? "light" : "dark";
    }, [light, pathname]);
    const toggle = () => {
        const next = !light;
        try {
            localStorage.setItem(themeKey, next ? "light" : "dark");
            fallbackLight = null;
        } catch {
            fallbackLight = next;
        }
        window.dispatchEvent(new Event(themeChanged));
    };
    return <ThemeContext.Provider value={{ light, toggle }}>{children}</ThemeContext.Provider>;
}

export function ThemeToggle() {
    const { light, toggle } = useContext(ThemeContext);
    return (
        <Button
            type="button"
            variant="icon"
            onClick={toggle}
            aria-label={`Switch to ${light ? "dark" : "light"} mode`}
        >
            {light ? <Moon size={18} /> : <Sun size={18} />}
        </Button>
    );
}
