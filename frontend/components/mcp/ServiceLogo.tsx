import { Plus } from "lucide-react";
import Image from "next/image";
import styles from "./mcp.module.css";

// Catalog ids with a vendored logo in public/mcp/<id>.png: each service's own app icon, a full
// square in its own colours, so it reads the same on both themes.
const LOGOS = new Set([
    "context7",
    "deepwiki",
    "huggingface",
    "cloudflare-docs",
    "github",
    "notion",
    "linear",
    "miro",
    "granola",
    "shaders",
    "jira",
    "stripe",
    "supabase",
    "neon",
    "vercel",
    "sentry",
]);

/** Which logo a service shows: its own (uploaded, or named by the server), the vendored one, or the default. */
const logoOf = (id: string, icon?: string | null) =>
    icon || (LOGOS.has(id) ? `/mcp/${id}.png` : "/mcp/default.png");

/** A service's logo at text size, for the composer's tag and its "/" menu. */
export function ServiceIcon({
    id,
    icon,
    className,
}: {
    id: string;
    icon?: string | null;
    className: string;
}) {
    return (
        <Image
            src={logoOf(id, icon)}
            alt=""
            width={16}
            height={16}
            // A data URI is already as small as it gets.
            unoptimized={Boolean(icon)}
            className={`${className} shrink-0 rounded-[3px] object-cover`}
        />
    );
}

/** A service's logo in its tile; "add" gets a plus. */
export function ServiceLogo({ id, icon }: { id: string; icon?: string | null }) {
    return (
        // A quiet tile with a hairline border; the icon sits inside it with its own small radius.
        <span
            aria-hidden="true"
            className="size-10 rounded-[8px] grid shrink-0 place-items-center border border-border bg-foreground/[0.04] text-muted-foreground"
        >
            {id === "add" ? (
                <Plus size={18} strokeWidth={1.75} />
            ) : (
                // Keyed by the image, so a new logo (an upload, or one the server named) fades in.
                <span
                    key={logoOf(id, icon)}
                    className={`${styles.reveal} size-6 rounded-[5px] relative overflow-hidden`}
                >
                    <Image
                        src={logoOf(id, icon)}
                        alt=""
                        fill
                        sizes="24px"
                        unoptimized={Boolean(icon)}
                        className="object-cover"
                    />
                </span>
            )}
        </span>
    );
}
