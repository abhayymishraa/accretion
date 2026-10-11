"use client";

import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useAppServices } from "@/hooks/appservices/useAppServices";
import { Check, Minus } from "lucide-react";
import type { ReactNode } from "react";
import { WorkspaceTabPanel } from "@/components/chat/WorkspaceTabPanel";

/** One way people can sign in to the app, on or off. */
function Method({ label, on }: { label: string; on: boolean }) {
    const Icon = on ? Check : Minus;
    return (
        <li className="flex min-h-9 items-center gap-2 text-[13px]">
            <Icon
                size={14}
                aria-hidden="true"
                className={on ? "text-emerald-700 dark:text-[#22c55e]" : "text-muted-foreground"}
            />
            <span className={on ? "" : "text-muted-foreground"}>{label}</span>
            <span className="ml-auto text-xs text-muted-foreground">{on ? "On" : "Off"}</span>
        </li>
    );
}

/** The workspace's App services tab: the sign-in Accretion gives the app. */
export function AppServicesPanel({ projectId }: { projectId: string }) {
    const { services, failed, retry } = useAppServices(projectId);

    let body: ReactNode;
    if (failed && !services)
        body = (
            <ErrorBox message="Couldn't load your app's services." onRetry={() => void retry()} />
        );
    else if (!services) body = <Skeleton className="h-24 rounded-[10px]" aria-label="Loading" />;
    else
        body = (
            <section
                aria-label="Sign-in"
                data-loaded-in=""
                className="rounded-[10px] border border-border bg-surface-2 px-3 py-3"
            >
                <h3 className="text-[13px] font-semibold">Sign-in</h3>
                <p className="mt-0.5 text-xs leading-[1.5] text-pretty text-muted-foreground">
                    Ways people can sign in to your app. Accretion handles the sign-in for it.
                </p>
                <ul className="mt-3">
                    <Method label="Google" on={services.sign_in.google} />
                    <Method label="Email link" on />
                </ul>
            </section>
        );

    return (
        <WorkspaceTabPanel
            title="App services"
            note="Sign-in your app can use without keys of its own."
        >
            {body}
        </WorkspaceTabPanel>
    );
}
