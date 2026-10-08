/** Steady state is the boring one, so it stays muted. Only trouble takes colour. */
export function ConnectionPill({
    connected,
    building,
    awaiting,
}: {
    connected: boolean;
    building: boolean;
    awaiting: boolean;
}) {
    const [label, dot, tone] = !connected
        ? ["Offline", "bg-destructive", "border-destructive/40 text-destructive"]
        : building
          ? ["Working", "bg-primary", "border-hairline text-foreground"]
          : awaiting
            ? ["Your turn", "bg-primary", "border-hairline text-foreground"]
            : // Idle is the one state a phone-width composer can drop: it has no room for it.
              [
                  "Live",
                  "bg-muted-foreground/50",
                  "border-transparent text-muted-foreground max-sm:hidden",
              ];
    return (
        <span
            className={`inline-flex h-7 shrink-0 items-center whitespace-nowrap gap-1.5 rounded-full border px-2.5 text-[11px] [transition:color_150ms_ease,border-color_150ms_ease] ${tone}`}
            role="status"
        >
            <span
                aria-hidden="true"
                className={`size-1.5 rounded-full [transition:background-color_150ms_ease] ${dot} ${
                    building || !connected ? "motion-safe:animate-pulse" : ""
                }`}
            />
            {label}
        </span>
    );
}
