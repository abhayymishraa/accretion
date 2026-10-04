import { ShieldAlert } from "lucide-react";

/** Shown wherever a skill comes in: its instructions reach the builder as they are. */
export function TrustNotice() {
    return (
        <div className="flex gap-3 border-b border-border bg-surface-1 px-5 py-4 sm:px-7">
            <ShieldAlert
                size={18}
                strokeWidth={1.75}
                className="mt-0.5 shrink-0 text-foreground"
                aria-hidden="true"
            />
            <p className="text-[13px] leading-[1.55] text-muted-foreground">
                <strong className="font-semibold text-foreground">Use trusted sources only.</strong>{" "}
                A skill copied from somewhere you do not trust can tell Accretion to do unsafe
                things.
            </p>
        </div>
    );
}
