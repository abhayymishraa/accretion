import { Brand } from "@/components/layout/Brand";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { EB_Garamond } from "next/font/google";
import Image from "next/image";
import Link from "next/link";
import { AUTH_ART } from "./authArt";
import styles from "./auth.module.css";

const display = EB_Garamond({
    subsets: ["latin"],
    weight: ["400", "500"],
    style: ["normal", "italic"],
    variable: "--font-display",
    display: "swap",
});

// The footer line under every auth form. Shared because it was written out six
// times and VerifyEmailPage drifted to a stale copy of it.
export const AUTH_SWITCH_LINK =
    "mt-6 text-center text-[13px] text-muted-foreground [&_a]:font-medium [&_a]:text-accent-foreground [&_a]:underline [&_a]:underline-offset-[3px] [&_a]:transition-opacity [&_a]:duration-150 pointer-fine:[&_a:hover]:opacity-75";

export function AuthFrame({
    signup = false,
    title,
    description,
    children,
}: {
    signup?: boolean;
    title?: string;
    description?: string;
    children: React.ReactNode;
}) {
    const switchHref = signup ? "/signin" : "/signup";
    const switchLabel = signup ? "Sign in" : "Create account";

    return (
        // Light-locked like the landing page: these two screens are one
        // doorway, and the workspace still carries its own theme toggle.
        <div
            data-palette="light"
            className={`${display.variable} ${styles.page} grid min-h-[100dvh] grid-cols-[1.05fr_1fr] max-lg:grid-cols-1`}
        >
            <a
                className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-full focus:bg-foreground focus:px-5 focus:py-3 focus:text-background"
                href="#main-content"
            >
                Skip to content
            </a>

            <section
                className={`${styles.photoPanel} relative isolate hidden flex-col justify-between overflow-clip p-10 text-white lg:flex [&_.ember-brand]:gap-2.5 [&_.ember-brand]:text-[19px] [&_.ember-brand]:text-white [&_.ember-brand>svg]:w-[22px]`}
            >
                <Image
                    src={AUTH_ART.src}
                    alt=""
                    fill
                    priority
                    quality={92}
                    sizes="(max-width: 1024px) 0px, 52vw"
                    placeholder="blur"
                    blurDataURL={AUTH_ART.blur}
                    style={{ objectPosition: AUTH_ART.pos }}
                    className={styles.art}
                />
                <div className={styles.scrim} />

                <div style={{ ["--i" as string]: 0 }} className={styles.rise}>
                    <Brand />
                </div>

                <div className="max-w-[30ch]">
                    <p
                        style={{ ["--i" as string]: 1 }}
                        className={`${styles.rise} font-mono text-[11px] tracking-[0.2em] text-white/90 uppercase`}
                    >
                        {signup ? "New workspace" : "Welcome back"}
                    </p>
                    {/* Signup gets the landing hero's mask reveal; signin gets the
                        plain rise. Never both — two entrances on one axis compose
                        into a faster, weaker move than either alone. */}
                    <p className="mt-5 font-[family-name:var(--font-display)] text-[clamp(30px,3.4vw,46px)] leading-[1.1] tracking-[-0.015em] text-balance [text-shadow:0_2px_30px_rgb(10_30_50_/_0.4)]">
                        <span
                            style={{ ["--i" as string]: signup ? 1 : 2 }}
                            className={`block ${signup ? styles.lineRise : styles.rise}`}
                        >
                            {signup ? "Every app begins" : "Pick up where"}
                        </span>
                        <em
                            style={{ ["--i" as string]: 2 }}
                            className={`block pb-1 leading-[1.18] font-medium italic ${
                                signup ? styles.lineRise : styles.rise
                            }`}
                        >
                            {signup ? "as a sentence." : "you left off."}
                        </em>
                    </p>
                    <p
                        style={{ ["--i" as string]: 3 }}
                        className={`${styles.rise} mt-5 text-[14.5px] leading-[1.65] text-white/85 text-pretty`}
                    >
                        {signup
                            ? "Describe what you want in plain words. Accretion writes it, builds it, and hands you every line."
                            : "Your projects, their source, and the conversation that made them are all where you left them."}
                    </p>
                </div>

                <p
                    style={{ ["--i" as string]: 2 }}
                    className={`${styles.rise} text-[12.5px] text-white/65`}
                >
                    © {new Date().getFullYear()} Accretion
                </p>
            </section>

            <main
                id="main-content"
                className="flex flex-col px-6 py-8 max-lg:min-h-[100dvh] lg:px-12 lg:py-10"
            >
                <div className="flex items-center justify-between gap-4">
                    <span className="lg:hidden [&_.ember-brand]:gap-2.5 [&_.ember-brand]:text-[19px] [&_.ember-brand>svg]:w-[22px]">
                        <Brand />
                    </span>
                    <Link
                        href={switchHref}
                        className={cn(
                            buttonVariants({ variant: "outlinePill" }),
                            "ml-auto h-10 pointer-coarse:h-11 justify-normal gap-0 border-foreground/20 px-4 text-[13.5px] whitespace-nowrap pointer-fine:hover:border-foreground/40",
                        )}
                    >
                        {switchLabel}
                    </Link>
                </div>

                <div
                    style={{ ["--i" as string]: 1 }}
                    className={`${styles.rise} mx-auto flex w-full max-w-[25rem] flex-1 flex-col justify-center py-10`}
                >
                    <h1 className="text-[clamp(26px,2.6vw,33px)] leading-[1.15] font-medium tracking-[-0.03em] text-balance">
                        {title || (signup ? "Create your workspace" : "Welcome back")}
                    </h1>
                    <p className="mt-3 text-[14.5px] leading-[1.6] text-muted-foreground text-pretty">
                        {description ||
                            (signup
                                ? "A place for your next good idea."
                                : "Sign in to continue making.")}
                    </p>
                    {children}
                </div>
            </main>
        </div>
    );
}
