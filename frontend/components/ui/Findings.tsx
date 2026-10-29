import type { DatabaseFinding } from "@/types/supabase.type";
import { ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";

const NOTE = "text-xs leading-[1.5] text-muted-foreground";

/** Security checks' findings, such as a table anyone can read, with how to fix each and what to do next. */
export function Findings({ findings, footer }: { findings: DatabaseFinding[]; footer: ReactNode }) {
    if (!findings.length) return null;
    return (
        <section aria-label="Things to fix" className="grid gap-1.5">
            <h3 className="text-xs font-semibold">Things to fix</h3>
            <ul className="grid gap-1.5">
                {findings.map((finding) => (
                    <li
                        key={`${finding.title}:${finding.detail}`}
                        className="rounded-[10px] border border-border bg-surface-2 px-3 py-2.5"
                    >
                        <p className="flex items-start gap-1.5 text-[13px] font-medium">
                            <ShieldAlert
                                size={14}
                                aria-hidden="true"
                                className={`mt-0.5 shrink-0 ${finding.level === "ERROR" ? "text-destructive" : "text-amber-700 dark:text-amber-300"}`}
                            />
                            {finding.title}
                        </p>
                        <p className={`${NOTE} mt-1`}>{finding.detail}</p>
                        <p className={`${NOTE} mt-1 text-foreground/85`}>{finding.remediation}</p>
                    </li>
                ))}
            </ul>
            {footer}
        </section>
    );
}
