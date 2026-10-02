"use client";

import { Brand } from "@/components/layout/Brand";
import { useWaitlist } from "@/hooks/auth/useWaitlist";
import { cn } from "@/lib/utils";
import Image from "next/image";
import type React from "react";
import styles from "./waitlist.module.css";

const label = "text-[12px] leading-[1.4] text-[var(--ink-subtle)]";

const steps = [
    {
        when: "Now",
        title: "We review your request",
        body: "We let people in by hand, a few each week, so everyone gets a good start.",
    },
    {
        when: "Your turn",
        title: "A sign-in email arrives",
        body: "One button signs you straight in. It works once and stays valid for 7 days.",
    },
    {
        when: "After that",
        title: "Sign in the usual way",
        body: "Use your email and password, or Google or GitHub, whenever you come back.",
    },
];

const questions = [
    {
        q: "How long will I wait?",
        a: "There is no fixed date. We approve people a few at a time and email you the moment your spot opens.",
    },
    {
        q: "I can't find the email",
        a: "Check your spam folder and, in Gmail, the Promotions tab for a message from Accretion.",
    },
];

function Enter({
    i,
    className,
    children,
}: {
    i: number;
    className?: string;
    children: React.ReactNode;
}) {
    return (
        <div className={cn(styles.enter, className)} style={{ "--i": i } as React.CSSProperties}>
            {children}
        </div>
    );
}

export default function WaitlistPage() {
    const { user, signOut } = useWaitlist();
    const first = user?.name.split(" ")[0];
    const joined = user?.created_at
        ? new Date(user.created_at).toLocaleDateString(undefined, { dateStyle: "long" })
        : "";
    return (
        <main className={cn(styles.root, "min-h-dvh overflow-x-hidden px-4 sm:px-8")}>
            <header className="mx-auto flex h-14 max-w-[1120px] items-center justify-between">
                {/* The page stays dark in either app theme, so the wordmark takes this page's ink. */}
                <span className="[&_a]:text-[var(--ink)]">
                    <Brand />
                </span>
                <button
                    type="button"
                    onClick={signOut}
                    className={cn(
                        styles.lift,
                        "h-9 cursor-pointer rounded-[8px] px-3.5 text-[14px] font-medium transition-[background-color,transform] duration-150 ease-out active:scale-[0.97] pointer-fine:hover:bg-[var(--surface-2)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]/50",
                    )}
                >
                    Sign out
                </button>
            </header>

            <div className="mx-auto max-w-[1120px] pt-16 pb-24 sm:pt-24">
                <Enter i={0}>
                    <span className="inline-flex items-center gap-2 rounded-full bg-[var(--surface-2)] px-2.5 py-0.5 text-[12px] text-[var(--ink-muted)]">
                        <span aria-hidden className="size-1.5 rounded-full bg-[var(--accent)]" />
                        On the waitlist
                    </span>
                </Enter>
                <Enter i={1}>
                    <h1 className="mt-5 max-w-[14ch] text-[clamp(2.4rem,5.4vw,3.5rem)] leading-[1.1] font-semibold tracking-[-0.032em] text-balance">
                        You&apos;re on the list{first ? `, ${first}` : ""}.
                    </h1>
                </Enter>
                <Enter i={2}>
                    <p className="mt-5 max-w-[46ch] text-[18px] leading-[1.5] tracking-[-0.006em] text-[var(--ink-subtle)]">
                        We let people in by hand, a few at a time. Your spot is saved, and we will
                        email you the moment it opens.
                    </p>
                </Enter>

                <Enter i={3} className="mt-14">
                    <section className={cn(styles.lift, "overflow-hidden rounded-[16px]")}>
                        <div className="relative aspect-[16/7] w-full max-sm:aspect-[4/3]">
                            <Image
                                src="/brand/waitlist-field.webp"
                                alt="Two kids in a green field looking up at an old ship overgrown with grass"
                                fill
                                priority
                                sizes="(min-width: 1120px) 1120px, 100vw"
                                className="object-cover object-[center_45%]"
                            />
                        </div>
                        <dl className="grid gap-px bg-[var(--hairline)] sm:grid-cols-4">
                            {[
                                ["Name", user?.name],
                                ["Email", user?.email],
                                ["Joined", joined],
                            ].map(([name, value]) => (
                                <div key={name} className="min-w-0 bg-[var(--surface-1)] px-6 py-5">
                                    <dt className={label}>{name}</dt>
                                    <dd className="mt-1 truncate text-[15px] text-[var(--ink)]">
                                        {value}
                                    </dd>
                                </div>
                            ))}
                            <div className="bg-[var(--surface-1)] px-6 py-5">
                                <dt className={label}>Email status</dt>
                                <dd className="mt-1.5">
                                    {user?.email_verified ? (
                                        <span className="rounded-full bg-[var(--success)]/15 px-2 py-0.5 text-[12px] text-[#5ccf73]">
                                            Confirmed
                                        </span>
                                    ) : (
                                        <span className="text-[14px] text-[var(--ink-muted)]">
                                            Open the link we emailed you
                                        </span>
                                    )}
                                </dd>
                            </div>
                        </dl>
                    </section>
                </Enter>

                <Enter i={4} className="mt-24">
                    <h2 className="text-[28px] leading-[1.2] font-semibold tracking-[-0.021em]">
                        What happens next
                    </h2>
                    <ol className="mt-8 border-t border-[var(--hairline)]">
                        {steps.map((step) => (
                            <li
                                key={step.title}
                                className="grid gap-2 border-b border-[var(--hairline)] py-6 sm:grid-cols-[180px_1fr] sm:gap-8"
                            >
                                <span
                                    className={cn(
                                        "text-[13px] font-medium tracking-[0.03em]",
                                        step.when === "Now"
                                            ? "text-[var(--accent)]"
                                            : "text-[var(--ink-tertiary)]",
                                    )}
                                >
                                    {step.when}
                                </span>
                                <div>
                                    <p className="text-[17px] font-medium tracking-[-0.01em]">
                                        {step.title}
                                    </p>
                                    <p className="mt-1 max-w-[60ch] text-[15px] leading-[1.5] text-[var(--ink-subtle)]">
                                        {step.body}
                                    </p>
                                </div>
                            </li>
                        ))}
                    </ol>
                </Enter>

                <Enter i={5} className="mt-24 grid gap-10 lg:grid-cols-[1.1fr_1fr]">
                    <section className={cn(styles.lift, "rounded-[12px] p-8 sm:p-12")}>
                        <h2 className="text-[28px] leading-[1.2] font-semibold tracking-[-0.021em]">
                            Want in sooner?
                        </h2>
                        <p className="mt-3 max-w-[42ch] text-[16px] leading-[1.5] text-[var(--ink-subtle)]">
                            Reply to your waitlist email and tell us the first app you&apos;d build.
                            Clear, specific ideas help us choose who goes next.
                        </p>
                    </section>
                    <section>
                        <h2 className="text-[20px] leading-[1.4] font-medium tracking-[-0.01em]">
                            Questions
                        </h2>
                        <div className="mt-4 border-t border-[var(--hairline)]">
                            {questions.map(({ q, a }) => (
                                <details
                                    key={q}
                                    className="group border-b border-[var(--hairline)]"
                                >
                                    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-[15px] font-medium [&::-webkit-details-marker]:hidden">
                                        {q}
                                        <span
                                            aria-hidden
                                            className="text-[var(--ink-tertiary)] transition-transform duration-200 ease-out group-open:rotate-45"
                                        >
                                            +
                                        </span>
                                    </summary>
                                    <p className="pb-5 text-[15px] leading-[1.5] text-[var(--ink-subtle)]">
                                        {a}
                                    </p>
                                </details>
                            ))}
                        </div>
                    </section>
                </Enter>
            </div>
        </main>
    );
}
