import type { UserData } from "@/types/auth.type";

/** Email plus credit balance, shared by both workspace headers so they cannot drift. */
export function AccountSummary({ userData }: { userData: UserData | null }) {
    return (
        <div className="ember-account flex items-center gap-3 text-[12px] text-muted-foreground min-w-0 [&>span:first-child]:max-w-55 [&>span:first-child]:overflow-hidden [&>span:first-child]:text-ellipsis [&>span:first-child]:whitespace-nowrap max-[1101px]:[&>span:first-child]:hidden max-md:hidden">
            {userData && (
                <>
                    <span>{userData.email}</span>
                    <span
                        className="ember-balance text-foreground bg-secondary py-1.5 px-2.5 rounded-[6px] whitespace-nowrap"
                        title="Credits left this month"
                    >
                        {userData.credits_unlimited
                            ? "Unlimited"
                            : `${userData.tokens_remaining} / ${userData.credits_limit} credits`}
                    </span>
                </>
            )}
        </div>
    );
}
