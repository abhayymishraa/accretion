"use client";

import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

export type SkillScope = "all" | "library" | "builtin";

interface SkillFiltersProps {
    query: string;
    onQuery: (query: string) => void;
    scope: SkillScope;
    onScope: (scope: SkillScope) => void;
    /** Skills in each scope, or null while the list loads. */
    counts: Record<SkillScope, number> | null;
}

const SCOPES: { value: SkillScope; label: string }[] = [
    { value: "all", label: "All" },
    { value: "library", label: "Yours" },
    { value: "builtin", label: "Built in" },
];

/** Search by name or description; the Skills page and the project's Skills and Connectors tabs size it their
 * own way. */
export function SkillSearch({
    value,
    onChange,
    className,
    label = "Search skills",
}: {
    value: string;
    onChange: (value: string) => void;
    className: string;
    label?: string;
}) {
    return (
        <label className="relative min-w-0 flex-1">
            <span className="sr-only">{label}</span>
            <Search
                size={14}
                aria-hidden="true"
                className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted-foreground"
            />
            {/* 16px on touch screens, so phones do not zoom in on focus. */}
            <Input
                type="search"
                value={value}
                onChange={(event) => onChange(event.target.value)}
                placeholder={label}
                className={`pl-9 pointer-coarse:h-11 pointer-coarse:text-[16px] ${className}`}
            />
        </label>
    );
}

/** Search by name or description, and narrow the page to one source. */
export function SkillFilters({ query, onQuery, scope, onScope, counts }: SkillFiltersProps) {
    return (
        <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <SkillSearch
                value={query}
                onChange={onQuery}
                className="h-11 rounded-none text-[16px] sm:h-9 sm:text-[13.5px]"
            />
            <div
                role="group"
                aria-label="Show"
                className="flex gap-px border border-border bg-border"
            >
                {SCOPES.map((option) => (
                    <button
                        key={option.value}
                        type="button"
                        aria-pressed={scope === option.value}
                        onClick={() => onScope(option.value)}
                        className="flex h-11 flex-1 items-center justify-center gap-1.5 bg-background px-3 text-[13px] whitespace-nowrap text-muted-foreground [transition:background-color_140ms_ease,color_140ms_ease,scale_100ms_var(--ease-out)] [&:not(:disabled)]:active:scale-[0.97] motion-reduce:[&:not(:disabled)]:active:scale-100 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring aria-pressed:bg-surface-2 aria-pressed:text-foreground sm:h-9 pointer-coarse:h-11 pointer-fine:hover:text-foreground"
                    >
                        {option.label}
                        {counts && (
                            <span
                                data-numeric=""
                                className="font-mono text-[11px] text-muted-foreground"
                            >
                                {counts[option.value]}
                            </span>
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
}
