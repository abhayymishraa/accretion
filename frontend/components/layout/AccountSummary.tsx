import { formatUsd } from "@/lib/auth/budget";
import type { UserData } from "@/types/auth.type";

/** Email plus budget balance, shared by both workspace headers so they cannot drift. */
export function AccountSummary({ userData }: { userData: UserData | null }) {
    // Sessions saved before the budget replaced credits hold an older shape until /auth/me reloads.
    const budget =
        typeof userData?.cost_allowance?.remaining_usd === "number"
            ? userData.cost_allowance
            : null;
    return (
        <div className="flex items-center gap-3 text-[12px] text-muted-foreground min-w-0 [&>span:first-child]:max-w-55 [&>span:first-child]:overflow-hidden [&>span:first-child]:text-ellipsis [&>span:first-child]:whitespace-nowrap max-[1101px]:[&>span:first-child]:hidden max-md:hidden">
            {userData && (
                <>
                    <span>{userData.email}</span>
                    {budget && (
                        <span
                            className="whitespace-nowrap rounded-[6px] bg-surface-2 px-2 py-1 font-mono tabular-nums text-foreground"
                            title="Build budget left this month"
                        >
                            {budget.unlimited
                                ? "Unlimited"
                                : `${formatUsd(budget.remaining_usd)} / ${formatUsd(budget.limit_usd)}`}
                        </span>
                    )}
                </>
            )}
        </div>
    );
}
