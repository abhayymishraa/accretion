"use client";

import { Brand } from "@/components/layout/Brand";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { useAdminUsers } from "@/hooks/admin/useAdminUsers";
import { cn } from "@/lib/utils";
import type { AccountRow, AccountStatus } from "@/types/auth.type";

const label = "text-[11px] tracking-[0.08em] text-muted-foreground uppercase";
const kbd =
    "rounded border border-border bg-surface-2 px-1.5 font-mono text-[11px] text-foreground";
const pill =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-[0.05em] whitespace-nowrap uppercase";
const tabs: { value: AccountStatus; name: string }[] = [
    { value: "waiting", name: "Waiting" },
    { value: "approved", name: "Approved" },
    { value: "all", name: "All" },
];

function day(value: string) {
    return new Date(value).toLocaleDateString(undefined, { dateStyle: "medium" });
}

// Muted tints so the account state reads in both themes.
function Status({ user }: { user: AccountRow }) {
    const [tint, text] = user.approved_at
        ? [
              "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
              `Approved ${day(user.approved_at)}`,
          ]
        : user.email_verified
          ? ["bg-amber-500/15 text-amber-700 dark:text-amber-300", "Waiting"]
          : ["bg-rose-500/15 text-rose-700 dark:text-rose-300", "Unconfirmed"];
    return <span className={cn(pill, tint)}>{text}</span>;
}

function Tile({
    name,
    value,
    note,
    first,
}: {
    name: string;
    value: number;
    note: string;
    first?: boolean;
}) {
    return (
        <div
            className={cn(
                "flex flex-col gap-1.5 rounded-xl border border-border bg-card p-6",
                first && "col-span-2 bg-surface-2 sm:col-span-1",
            )}
        >
            <span className={label}>{name}</span>
            <data value={value} className="font-serif text-[44px] leading-none tracking-[-0.03em]">
                {value}
            </data>
            <span className="text-[13px] text-muted-foreground">{note}</span>
        </div>
    );
}

export default function AdminPage() {
    const admin = useAdminUsers();
    const { data, items, selected, pending } = admin;
    const first = data && data.total ? (data.page - 1) * data.page_size + 1 : 0;
    const last = data ? Math.min(data.page * data.page_size, data.total) : 0;
    return (
        <main className="min-h-dvh overflow-x-hidden bg-background px-4 pb-20 text-foreground sm:px-8">
            <header className="mx-auto flex max-w-5xl items-center justify-between gap-4 border-b border-border py-4">
                <Brand />
                <Button type="button" variant="utility" onClick={admin.signOut}>
                    Sign out
                </Button>
            </header>
            <div className="mx-auto max-w-5xl">
                <div className="pt-12 pb-7">
                    <p className={label}>Admin</p>
                    <h1 className="font-serif text-[clamp(2rem,4.4vw,2.8rem)] leading-tight font-normal tracking-[-0.03em]">
                        Waitlist
                    </h1>
                </div>

                {admin.error ? (
                    <div className="mb-6">
                        <ErrorBox message={admin.error} />
                    </div>
                ) : null}

                {data ? (
                    <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-[1.4fr_1fr_1fr]">
                        <Tile
                            first
                            name="Waiting now"
                            value={data.counts.waiting}
                            note="Approved by hand"
                        />
                        <Tile name="Approved" value={data.counts.approved} note="All time" />
                        <Tile
                            name="Unconfirmed"
                            value={data.counts.unconfirmed}
                            note="Haven't clicked the link"
                        />
                    </div>
                ) : (
                    <p role="status" className="mb-8 text-muted-foreground">
                        Loading accounts…
                    </p>
                )}

                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                    <div role="group" aria-label="Account status" className="flex gap-1">
                        {tabs.map((tab) => (
                            <Button
                                key={tab.value}
                                type="button"
                                variant="tab"
                                aria-pressed={admin.status === tab.value}
                                onClick={() => admin.changeStatus(tab.value)}
                            >
                                {tab.name}
                            </Button>
                        ))}
                    </div>
                    <Input
                        type="search"
                        aria-label="Search by name or email"
                        maxLength={100}
                        placeholder="Search name or email"
                        value={admin.query}
                        onChange={(event) => admin.setQuery(event.target.value)}
                        className="w-full sm:w-72"
                    />
                </div>

                <div className="grid overflow-hidden rounded-xl border border-border bg-card md:min-h-[440px] md:grid-cols-[300px_minmax(0,1fr)]">
                    <ul
                        aria-label="Accounts"
                        className="max-h-[240px] overflow-y-auto border-b border-border md:max-h-[560px] md:border-r md:border-b-0"
                    >
                        {data && items.length === 0 ? (
                            <li className="p-6 text-center text-muted-foreground">
                                No accounts match.
                            </li>
                        ) : null}
                        {items.map((user) => (
                            <li key={user.id}>
                                <button
                                    type="button"
                                    aria-current={selected?.id === user.id}
                                    onClick={() => admin.select(user.id)}
                                    className="grid w-full cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-border px-5 py-3.5 text-left transition-colors pointer-fine:hover:bg-surface-2 aria-[current=true]:bg-surface-2 aria-[current=true]:shadow-[inset_3px_0_0_var(--foreground)]"
                                >
                                    <span className="min-w-0">
                                        <span className="block truncate font-medium">
                                            {user.name}
                                        </span>
                                        <span className="block truncate text-[13px] text-muted-foreground">
                                            {user.email}
                                        </span>
                                    </span>
                                    <span className="font-mono text-[12px] text-muted-foreground">
                                        {day(user.created_at)}
                                    </span>
                                </button>
                            </li>
                        ))}
                    </ul>

                    <div className="flex flex-col gap-7 p-6 md:p-10">
                        {selected ? (
                            <>
                                <div>
                                    <p className={label}>Joined {day(selected.created_at)}</p>
                                    <h2 className="mt-1.5 font-serif text-[34px] leading-tight font-normal tracking-[-0.03em] wrap-anywhere">
                                        {selected.name}
                                    </h2>
                                </div>
                                <dl className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-x-6 border-t border-border">
                                    <div className="min-w-0 border-b border-border py-4">
                                        <dt className={label}>Email</dt>
                                        <dd className="mt-1 wrap-anywhere">{selected.email}</dd>
                                    </div>
                                    <div className="border-b border-border py-4">
                                        <dt className={label}>Email confirmed</dt>
                                        <dd className="mt-1">
                                            {selected.email_verified ? "Yes" : "Not yet"}
                                        </dd>
                                    </div>
                                    <div className="border-b border-border py-4">
                                        <dt className={label}>Status</dt>
                                        <dd className="mt-1">
                                            <Status user={selected} />
                                        </dd>
                                    </div>
                                </dl>
                                {selected.approved_at ? null : (
                                    <>
                                        <div className="flex flex-wrap items-center gap-4">
                                            <Button
                                                type="button"
                                                disabled={pending !== null}
                                                onClick={() => admin.approve(selected.id)}
                                            >
                                                {pending === selected.id
                                                    ? "Sending…"
                                                    : "Approve and send sign-in email"}
                                            </Button>
                                            <span className="text-[12.5px] text-muted-foreground max-md:hidden">
                                                <kbd className={kbd}>A</kbd> approve{" "}
                                                <kbd className={kbd}>J</kbd>{" "}
                                                <kbd className={kbd}>K</kbd> next / previous
                                            </span>
                                        </div>
                                        <p className="text-[13.5px] text-muted-foreground">
                                            They get one email with a sign-in button that works
                                            once, for 7 days.
                                        </p>
                                    </>
                                )}
                            </>
                        ) : (
                            <p className="m-auto text-center text-muted-foreground">
                                {!data
                                    ? ""
                                    : items.length
                                      ? "That account isn't on this page. Pick someone from the list or search for them."
                                      : "Nobody here. New signups show up under Waiting."}
                            </p>
                        )}
                    </div>
                </div>

                {data && data.total > data.page_size ? (
                    <nav
                        aria-label="Pages"
                        className="mt-4 flex items-center justify-between gap-3 text-[13px]"
                    >
                        <span className="text-muted-foreground">
                            {first}-{last} of {data.total}
                        </span>
                        <div className="flex gap-2">
                            <Button
                                type="button"
                                variant="secondary"
                                disabled={data.page === 1}
                                onClick={() => admin.setPage(data.page - 1)}
                            >
                                Previous
                            </Button>
                            <Button
                                type="button"
                                variant="secondary"
                                disabled={last >= data.total}
                                onClick={() => admin.setPage(data.page + 1)}
                            >
                                Next
                            </Button>
                        </div>
                    </nav>
                ) : null}
            </div>
        </main>
    );
}
