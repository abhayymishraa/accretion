import type { ReactNode } from "react";

/** A workspace tab's frame: its title and note, then a body that scrolls clear of the home bar. */
export function WorkspaceTabPanel({
    title,
    note,
    children,
}: {
    title: string;
    note: string;
    children: ReactNode;
}) {
    return (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-1">
            <header className="border-b border-border px-4 py-3">
                <h2 className="text-sm font-semibold text-foreground">{title}</h2>
                <p className="mt-1 max-w-[60ch] text-xs leading-[1.5] text-pretty text-muted-foreground">
                    {note}
                </p>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4 pb-[calc(16px+env(safe-area-inset-bottom))]">
                {children}
            </div>
        </div>
    );
}
