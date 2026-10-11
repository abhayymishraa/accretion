"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { useDatabaseChoices } from "@/hooks/supabase/useProjectDatabase";
import type { LinkDatabase, SupabaseOrganization } from "@/types/supabase.type";
import { ChevronDown } from "lucide-react";
import { useId, useState, type ComponentProps } from "react";

// A segment's text; the selected background is one thumb behind them that slides to the choice.
const MODE =
    "relative flex-1 rounded-[7px] px-3 text-[12.5px] font-medium text-muted-foreground min-h-9 pointer-coarse:min-h-11 [transition:color_130ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 aria-pressed:text-foreground focus-visible:outline-2 focus-visible:outline-ring cursor-pointer";
const MODES = [
    ["create", "New project"],
    ["existing", "Project I have"],
] as const;

// A native select, dressed like the shared Input: the phone's own picker is the best one there is. Its own arrow
// sits against the border, so it is hidden and drawn inset.
function Select(props: ComponentProps<"select">) {
    return (
        <span className="relative flex items-center">
            <select
                {...props}
                className="h-10 w-full min-w-0 cursor-pointer appearance-none truncate rounded-[9px] border border-border bg-surface-2 pr-9 pl-3 text-[16px] text-foreground shadow-xs outline-none focus-visible:border-input focus-visible:ring-[3px] focus-visible:ring-ring/35 disabled:opacity-50 pointer-coarse:h-11 sm:text-[13px]"
            />
            <ChevronDown
                aria-hidden="true"
                className="pointer-events-none absolute right-3 size-4 text-muted-foreground"
            />
        </span>
    );
}

/** Pick where the app's database goes: a new Supabase project, or one the user already has. */
export function LinkDatabaseForm({
    organizations,
    link,
}: {
    organizations: SupabaseOrganization[];
    link: (body: LinkDatabase) => Promise<string>;
}) {
    const id = useId();
    const [mode, setMode] = useState<"create" | "existing">("create");
    // The fields fade in only after the user switches, not when the form first appears.
    const [switched, setSwitched] = useState(false);
    const [org, setOrg] = useState(organizations[0]?.id ?? "");
    const [name, setName] = useState("");
    const [region, setRegion] = useState("");
    const [ref, setRef] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const { regions, projects, failed } = useDatabaseChoices(mode === "existing" ? org : "");
    const chosenRegion = region || regions?.[0]?.id || "";

    if (!organizations.length)
        return (
            <p className="text-xs leading-[1.5] text-muted-foreground">
                Your Supabase account has no organizations yet. Make one on Supabase, then come
                back.
            </p>
        );

    return (
        <form
            className="grid gap-3"
            onSubmit={async (event) => {
                event.preventDefault();
                if (mode === "create" && !name.trim()) return setError("Give the project a name.");
                if (mode === "existing" && !ref) return setError("Choose a project.");
                setBusy(true);
                const failure = await link(
                    mode === "create"
                        ? { mode, organization_id: org, name: name.trim(), region: chosenRegion }
                        : { mode, ref },
                );
                setBusy(false);
                setError(failure);
            }}
        >
            <div
                role="group"
                aria-label="Where the database goes"
                className="relative flex gap-1 rounded-[9px] bg-surface-2 p-1"
            >
                <span
                    aria-hidden="true"
                    className="absolute inset-y-1 left-1 w-[calc((100%-12px)/2)] rounded-[7px] bg-background shadow-xs transition-transform duration-200 ease-[var(--ease-out)] motion-reduce:transition-none"
                    style={{
                        transform: mode === "existing" ? "translateX(calc(100% + 4px))" : undefined,
                    }}
                />
                {MODES.map(([value, label]) => (
                    <button
                        key={value}
                        type="button"
                        className={MODE}
                        aria-pressed={mode === value}
                        onClick={() => {
                            setMode(value);
                            setSwitched(true);
                        }}
                    >
                        {label}
                    </button>
                ))}
            </div>
            <label className="grid gap-1 text-xs text-muted-foreground" htmlFor={`${id}-org`}>
                Organization
                <Select
                    id={`${id}-org`}
                    value={org}
                    onChange={(event) => {
                        setOrg(event.target.value);
                        // A project belongs to one organization.
                        setRef("");
                    }}
                >
                    {organizations.map((item) => (
                        <option key={item.id} value={item.id}>
                            {item.name}
                        </option>
                    ))}
                </Select>
            </label>
            {mode === "create" ? (
                <>
                    <label
                        data-loaded-in={switched ? "" : undefined}
                        className="grid gap-1 text-xs text-muted-foreground"
                        htmlFor={`${id}-name`}
                    >
                        Project name
                        <Input
                            id={`${id}-name`}
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            autoComplete="off"
                            maxLength={256}
                            className="h-10 pointer-coarse:h-11 sm:text-[13px]"
                        />
                    </label>
                    <label
                        data-loaded-in={switched ? "" : undefined}
                        className="grid gap-1 text-xs text-muted-foreground"
                        htmlFor={`${id}-region`}
                    >
                        Region (closest to your users is fastest)
                        <Select
                            id={`${id}-region`}
                            value={chosenRegion}
                            disabled={!regions}
                            onChange={(event) => setRegion(event.target.value)}
                        >
                            {(regions ?? []).map((item) => (
                                <option key={item.id} value={item.id}>
                                    {item.name}
                                </option>
                            ))}
                        </Select>
                    </label>
                </>
            ) : (
                <label
                    data-loaded-in={switched ? "" : undefined}
                    className="grid gap-1 text-xs text-muted-foreground"
                    htmlFor={`${id}-ref`}
                >
                    Project
                    <Select
                        id={`${id}-ref`}
                        value={ref}
                        disabled={!projects?.length}
                        onChange={(event) => setRef(event.target.value)}
                    >
                        <option value="">
                            {!projects
                                ? "Loading…"
                                : projects.length
                                  ? "Choose a project"
                                  : "No projects here"}
                        </option>
                        {(projects ?? []).map((item) => (
                            <option key={item.ref} value={item.ref}>
                                {item.name} · {item.region}
                            </option>
                        ))}
                    </Select>
                </label>
            )}
            <p className="text-xs leading-[1.5] text-muted-foreground">
                Connecting copies your app&apos;s data to Supabase. From then on, your app keeps its
                data there.
            </p>
            <Button
                type="submit"
                disabled={busy || (mode === "create" && !chosenRegion)}
                className="max-sm:w-full sm:justify-self-start"
            >
                {busy ? "Connecting…" : "Connect database"}
            </Button>
            <ErrorBox
                message={error || (failed ? "Couldn't load the choices from Supabase." : "")}
                className="text-xs"
            />
        </form>
    );
}
