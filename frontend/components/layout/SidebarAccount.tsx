"use client";

import { useLightTheme, useThemeToggle } from "@/components/layout/ThemeProvider";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatUsd } from "@/lib/auth/budget";
import type { UserData } from "@/types/auth.type";
import { LogOut, Moon, Settings, Sun } from "lucide-react";
import Link from "next/link";

const PILL =
    "flex h-9 cursor-pointer items-center rounded-[8px] border border-border bg-surface-2 text-[12.5px] [transition:background-color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-1";

/** The sidebar foot, as v0 lays it out: the account menu, and the month's budget beside it. */
export function SidebarAccount({
    userData,
    onSignOut,
}: {
    userData: UserData | null;
    onSignOut: () => void;
}) {
    const light = useLightTheme();
    const toggleTheme = useThemeToggle();
    if (!userData) return null;
    const name = userData.name || userData.email.split("@")[0];
    const budget =
        typeof userData.cost_allowance?.remaining_usd === "number" ? userData.cost_allowance : null;
    const balance = budget?.unlimited ? "∞" : budget ? formatUsd(budget.remaining_usd) : "";
    return (
        <div className="flex items-center gap-2">
            <DropdownMenu>
                <DropdownMenuTrigger
                    aria-label={`Account: ${name}`}
                    className={`${PILL} min-w-0 flex-1 gap-2 px-2 group-data-[collapsed=true]/sidebar:justify-center group-data-[collapsed=true]/sidebar:border-transparent group-data-[collapsed=true]/sidebar:bg-transparent group-data-[collapsed=true]/sidebar:px-0`}
                >
                    <span
                        aria-hidden="true"
                        className="grid size-6 shrink-0 place-items-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground"
                    >
                        {name.charAt(0).toUpperCase()}
                    </span>
                    <span className="min-w-0 truncate group-data-[collapsed=true]/sidebar:hidden">
                        {name}
                    </span>
                </DropdownMenuTrigger>
                <DropdownMenuContent side="top" align="start" className="w-64">
                    <div className="px-2 py-1.5">
                        <p className="m-0 truncate text-[13px] text-foreground">{name}</p>
                        <p className="m-0 truncate text-[12px] text-muted-foreground">
                            {userData.email}
                        </p>
                    </div>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                        <Link href="/profile" className="justify-between">
                            Settings
                            <Settings aria-hidden="true" />
                        </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <div className="flex items-center justify-between px-2 py-1 text-sm">
                        Theme
                        <span className="flex rounded-full border border-border p-0.5">
                            {[
                                { value: false, label: "Dark", Icon: Moon },
                                { value: true, label: "Light", Icon: Sun },
                            ].map(({ value, label, Icon }) => (
                                <button
                                    key={label}
                                    type="button"
                                    aria-label={`${label} theme`}
                                    aria-pressed={light === value}
                                    onClick={() => light !== value && toggleTheme()}
                                    className="grid size-7 cursor-pointer place-items-center rounded-full text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] aria-pressed:bg-surface-2 aria-pressed:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                                >
                                    <Icon size={14} />
                                </button>
                            ))}
                        </span>
                    </div>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onSelect={onSignOut} className="justify-between">
                        Sign out
                        <LogOut aria-hidden="true" />
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
            {budget && (
                <Popover>
                    <PopoverTrigger
                        className={`${PILL} shrink-0 px-2.5 font-mono tabular-nums group-data-[collapsed=true]/sidebar:hidden`}
                        aria-label="Build budget"
                    >
                        {balance}
                    </PopoverTrigger>
                    <PopoverContent
                        side="top"
                        align="end"
                        collisionPadding={12}
                        className="w-64 text-[13px]"
                    >
                        <p className="m-0 mb-2 text-muted-foreground">Build budget</p>
                        {budget.unlimited ? (
                            <p className="m-0">Unlimited on your plan.</p>
                        ) : (
                            <dl className="m-0 grid grid-cols-[1fr_auto] gap-y-1.5 [&_dd]:m-0 [&_dd]:font-mono [&_dd]:tabular-nums">
                                <dt>Monthly budget</dt>
                                <dd>{formatUsd(budget.limit_usd)}</dd>
                                <dt>Used</dt>
                                <dd>{formatUsd(budget.limit_usd - budget.remaining_usd)}</dd>
                                <dt>Left</dt>
                                <dd>{formatUsd(budget.remaining_usd)}</dd>
                            </dl>
                        )}
                        <p className="m-0 mt-3 text-[12px] text-muted-foreground">
                            Resets{" "}
                            {new Date(budget.resets_at).toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                            })}
                            . Covers model use only; previews do not count.
                        </p>
                    </PopoverContent>
                </Popover>
            )}
        </div>
    );
}
