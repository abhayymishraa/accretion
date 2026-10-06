"use client";

import { Button } from "@/components/ui/button";

import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { ProfileIdentityCard } from "@/components/profile/ProfileIdentityCard";
import { ProfileSkeleton } from "@/components/profile/ProfileSkeleton";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Check, Mail } from "lucide-react";
import { SiGithub, SiGoogle } from "react-icons/si";

import { useProfile } from "@/hooks/profile/useProfile";
import { formatUsd } from "@/lib/auth/budget";

export default function ProfilePage() {
    const { user, options, busy, error, message, setAttempt, signOut, save, connect } =
        useProfile();
    const budget = user?.cost_allowance;
    return (
        <>
            <div className="ember-workspace-shell flex min-h-dvh [&>.ember-workspace]:flex-1 [&>.ember-workspace]:min-w-0 [&>.ember-workspace]:w-full [&>.ember-workspace]:mx-auto">
                <WorkspaceSidebar userData={user} onSignOut={signOut} />
                <main
                    className="ember-profile w-full min-w-0 max-w-275 mx-auto py-9.5 px-[clamp(20px,_4vw,_56px)] max-md:py-6 max-md:px-4.5"
                    id="main-content"
                >
                    <div className="ember-profile-heading mb-6.5 [&_h1]:text-[clamp(28px,_3vw,_36px)] [&_h1]:tracking-[-1.3px] [&_h1]:font-medium [&_h1]:my-1.5 [&_h1]:mx-0 [&>p:last-child]:text-[14px] [&>p:last-child]:leading-[1.6] [&>p:last-child]:text-muted-foreground">
                        <p className="ember-eyebrow uppercase tracking-[0.12em] text-[10px] font-medium text-accent-foreground mb-5.5">
                            Your workspace, your way
                        </p>
                        <h1>Profile</h1>
                        <p>A little about the person behind the ideas.</p>
                    </div>
                    <ErrorBox message={error} />
                    {!user ? (
                        error ? (
                            <div className="ember-profile-loading py-10">
                                <Button variant="default" onClick={() => setAttempt((v) => v + 1)}>
                                    Try again
                                </Button>
                            </div>
                        ) : (
                            <ProfileSkeleton />
                        )
                    ) : (
                        <div data-loaded-in="">
                            <ProfileIdentityCard user={user} busy={busy} onSave={save} />
                            <div className="mt-9 grid gap-8 md:grid-cols-2 md:gap-12 [&_h2]:mb-1.5 [&_h2]:text-[17px] [&_h2]:font-medium [&_section>p]:text-sm [&_section>p]:leading-relaxed [&_section>p]:text-muted-foreground">
                                {budget && (
                                    <section aria-labelledby="budget-title">
                                        <h2 id="budget-title">Monthly build budget</h2>
                                        <p className="mt-4 text-3xl! font-medium text-foreground!">
                                            {budget.unlimited ? (
                                                "Unlimited"
                                            ) : (
                                                <>
                                                    {formatUsd(budget.remaining_usd)}
                                                    <span className="text-muted-foreground">
                                                        {" / "}
                                                        {formatUsd(budget.limit_usd)}
                                                    </span>
                                                </>
                                            )}
                                        </p>
                                        <p className="mt-2">
                                            {budget.unlimited
                                                ? "No budget limit applies to this account."
                                                : "Covers the AI that builds your projects. Previews do not count against it."}
                                        </p>
                                        {!budget.unlimited && (
                                            <p className="mt-4 text-sm text-muted-foreground">
                                                Resets {formatReset(budget.resets_at)}
                                            </p>
                                        )}
                                    </section>
                                )}
                                <section aria-labelledby="signin-title">
                                    <h2 id="signin-title">Sign-in methods</h2>
                                    <p>Keep your ideas within reach.</p>
                                    <div className="ember-profile-methods mt-4.5 [&>div]:flex [&>div]:items-center [&>div]:gap-[13px] [&>div]:min-h-[75px] [&>div]:border-b [&>div]:border-b-border [&>div>svg]:shrink-0 [&_span]:flex-1 [&_span]:text-[14px] [&_small]:block [&_small]:text-muted-foreground [&_small]:text-[12px] [&_small]:mt-1 [&_button]:py-2.5 [&_button]:px-3.5">
                                        {(["google", "github"] as const).map((provider) => {
                                            const connected = user.providers?.includes(provider);
                                            return (
                                                <div key={provider}>
                                                    {provider === "google" ? (
                                                        <SiGoogle aria-hidden="true" />
                                                    ) : (
                                                        <SiGithub aria-hidden="true" />
                                                    )}
                                                    <span>
                                                        {provider === "google"
                                                            ? "Google"
                                                            : "GitHub"}
                                                        <small>
                                                            {connected
                                                                ? "Connected"
                                                                : options?.providers[provider]
                                                                  ? "Not connected"
                                                                  : "Awaiting setup"}
                                                        </small>
                                                    </span>
                                                    {connected ? (
                                                        <Check size={17} aria-label="Connected" />
                                                    ) : (
                                                        <Button
                                                            variant="secondary"
                                                            disabled={
                                                                busy ||
                                                                !options?.providers[provider]
                                                            }
                                                            onClick={() => connect(provider)}
                                                        >
                                                            Connect
                                                        </Button>
                                                    )}
                                                </div>
                                            );
                                        })}
                                        <div>
                                            <Mail size={18} />
                                            <span>
                                                Email
                                                <small>
                                                    {user.email_verified
                                                        ? "Verified"
                                                        : "Not verified"}
                                                </small>
                                            </span>
                                            {user.email_verified && (
                                                <Check size={17} aria-label="Verified" />
                                            )}
                                        </div>
                                    </div>
                                </section>
                            </div>
                            <p
                                className="ember-profile-status min-h-6 mt-5 text-accent-foreground text-[14px]"
                                role="status"
                            >
                                {message && (
                                    <span key={message} data-loaded-in>
                                        {message}
                                    </span>
                                )}
                            </p>
                        </div>
                    )}
                </main>
            </div>
        </>
    );
}

/** The budget resets on the first of the month, UTC. */
function formatReset(resetAt?: string | null) {
    const next = new Date(resetAt ?? "");
    return Number.isNaN(next.getTime())
        ? "on the 1st, UTC"
        : `${next.toLocaleDateString(undefined, {
              day: "numeric",
              month: "long",
              timeZone: "UTC",
          })}, UTC`;
}
