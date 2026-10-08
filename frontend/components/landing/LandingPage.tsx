import { BuildPlate } from "@/components/landing/BuildPlate";
import { FaqItem } from "@/components/landing/FaqItem";
import styles from "@/components/landing/landing.module.css";
import { MeadowFooter } from "@/components/landing/MeadowFooter";
import { StepStamps } from "@/components/landing/StepStamps";
import { Brand } from "@/components/layout/Brand";
import { ArrowUpRight } from "lucide-react";
import { readFileSync } from "node:fs";
import { EB_Garamond } from "next/font/google";
import Image from "next/image";
import Link from "next/link";
import path from "node:path";

const display = EB_Garamond({
    subsets: ["latin"],
    weight: ["400", "500"],
    style: ["normal", "italic"],
    variable: "--font-display",
    display: "swap",
});

const PHOTO = "/brand/meadow-source.png";
const blurDataURL = readFileSync(path.join(process.cwd(), "public/brand/meadow.lqip.txt"), "utf8");

const QUESTIONS: [string, string][] = [
    [
        "What can I build?",
        "Web apps: dashboards, tools, portfolios, trackers. Anything a React project can be.",
    ],
    [
        "Can I change the result?",
        "Yes. Keep talking to it, or edit the files yourself in the workspace.",
    ],
    ["Can I take the code with me?", "Always. Download the project as a ZIP and run it anywhere."],
    [
        "What happens when I stop a run?",
        "It stops cleanly. Everything written up to that point is kept.",
    ],
    [
        "How does usage work?",
        "Your account carries a generation balance. A build spends it; browsing does not.",
    ],
];

// Press feedback and hover are gated behind fine pointers so touch devices do
// not trigger a stuck hover on tap. Everything over the photograph is glass, so
// no control punches a dark hole in the picture.
const CONTROL =
    "group inline-flex items-center gap-2 rounded-full text-[14.5px] font-medium text-white transition-[transform,background-color,box-shadow] duration-[160ms] ease-[var(--ease-out)] active:scale-[0.97]";
const PRIMARY = `${CONTROL} ${styles.glassFill} ${styles.glassBlur} h-12 pr-2 pl-6 pointer-fine:hover:bg-[rgb(10_30_50_/_0.46)]`;
const SECONDARY =
    "inline-flex h-12 items-center rounded-full bg-white px-6 text-[14.5px] font-medium text-[#10212f] shadow-[0_10px_30px_-12px_rgb(10_30_50_/_0.5)] transition-transform duration-[160ms] ease-[var(--ease-out)] active:scale-[0.97]";

export default function LandingPage() {
    return (
        <div data-palette="light" className={`${display.variable} ${styles.page} min-h-[100dvh]`}>
            <a
                className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-full focus:bg-foreground focus:px-5 focus:py-3 focus:text-background"
                href="#main-content"
            >
                Skip to content
            </a>

            <section
                className={`${styles.hero} flex min-h-[100dvh] flex-col items-center px-5 pt-5 pb-16 text-white`}
                aria-labelledby="hero-heading"
            >
                <Image
                    src={PHOTO}
                    alt=""
                    aria-hidden="true"
                    fill
                    priority
                    quality={92}
                    sizes="100vw"
                    placeholder="blur"
                    blurDataURL={blurDataURL}
                    className={styles.heroPhoto}
                />
                <div className={styles.heroScrim} aria-hidden="true" />

                <header
                    style={{ ["--i" as string]: 0 }}
                    className={`${styles.heroRise} ${styles.island} flex h-14 w-max max-w-full items-center gap-5 rounded-full py-1 pr-1.5 pl-5 [&_.ember-brand]:gap-2 [&_.ember-brand]:text-[17px] [&_.ember-brand]:text-white [&_.ember-brand>svg]:w-[21px]`}
                >
                    <span
                        style={{ ["--i" as string]: 0 }}
                        className={`${styles.heroRise} inline-flex`}
                    >
                        <Brand />
                    </span>
                    <nav
                        aria-label="Primary"
                        style={{ ["--i" as string]: 0.5 }}
                        className={`${styles.heroRise} flex items-center gap-6 text-[13.5px] text-white max-md:hidden [&_a]:transition-colors [&_a]:duration-150 pointer-fine:[&_a:hover]:text-white`}
                    >
                        <Link href="#how-it-works">How it works</Link>
                        <Link href="#faq">Questions</Link>
                        <Link href="/signin">Sign in</Link>
                    </nav>
                    <Link
                        href="/chat"
                        style={{ ["--i" as string]: 1 }}
                        className={`${styles.heroRise} ${CONTROL} ${styles.glassFill} h-11 pr-1.5 pl-5 pointer-fine:hover:bg-[rgb(10_30_50_/_0.46)]`}
                    >
                        Start building
                        <span className="flex size-8 items-center justify-center rounded-full bg-white/20 transition-transform duration-[160ms] ease-[var(--ease-out)] pointer-fine:group-hover:translate-x-[2px] pointer-fine:group-hover:-translate-y-px">
                            <ArrowUpRight size={15} aria-hidden="true" />
                        </span>
                    </Link>
                </header>

                <div className="mx-auto flex w-full max-w-[56rem] flex-col items-center pt-[6vh] text-center">
                    <h1
                        id="hero-heading"
                        className="font-[family-name:var(--font-display)] text-[clamp(40px,6.6vw,86px)] leading-[1.06] tracking-[-0.015em] text-balance [text-shadow:0_2px_30px_rgb(10_30_50_/_0.4)]"
                    >
                        <span
                            style={{ ["--i" as string]: 1 }}
                            className={`${styles.lineRise} block`}
                        >
                            Every app begins
                        </span>
                        <em
                            style={{ ["--i" as string]: 2 }}
                            className={`${styles.lineRise} block pb-1 leading-[1.14] font-medium italic`}
                        >
                            as a sentence.
                        </em>
                    </h1>
                    <p
                        style={{ ["--i" as string]: 3 }}
                        className={`${styles.heroRise} mt-5 max-w-[42ch] text-[16.5px] leading-[1.62] text-white/92 text-pretty [text-shadow:0_1px_18px_rgb(10_30_50_/_0.45)]`}
                    >
                        Say what you want in plain words. Accretion writes it, builds it, and shows
                        you the result.
                    </p>
                    <div
                        style={{ ["--i" as string]: 4 }}
                        className={`${styles.heroRise} mt-7 flex flex-wrap items-center justify-center gap-3`}
                    >
                        <Link href="/chat" className={PRIMARY}>
                            Start building
                            <span className="flex size-9 items-center justify-center rounded-full bg-white/20 transition-transform duration-[160ms] ease-[var(--ease-out)] pointer-fine:group-hover:translate-x-[2px] pointer-fine:group-hover:-translate-y-px">
                                <ArrowUpRight size={16} aria-hidden="true" />
                            </span>
                        </Link>
                        <Link href="#how-it-works" className={SECONDARY}>
                            See how it works
                        </Link>
                    </div>
                </div>
            </section>

            <main id="main-content" className="mx-auto w-full max-w-[72rem] px-6">
                <BuildPlate />
                <StepStamps />

                <section
                    style={{ ["--i" as string]: 0 }}
                    className={`${styles.reveal} ${styles.ruleTop} py-24 max-md:py-16`}
                    id="faq"
                    aria-labelledby="faq-heading"
                >
                    <h2
                        id="faq-heading"
                        className="mx-auto max-w-[18ch] text-center text-[clamp(28px,3.2vw,40px)] leading-[1.15] font-medium tracking-[-0.03em] text-balance"
                    >
                        A few useful answers.
                    </h2>
                    <div className="mx-auto mt-10 grid max-w-[64rem] grid-cols-2 gap-x-14 max-md:grid-cols-1 [&_details]:border-b [&_details]:border-border [&_details[open]_summary>span]:rotate-45 [&_details_p]:pb-5.5 [&_details_p]:text-[14px] [&_details_p]:leading-[1.8] [&_details_p]:text-muted-foreground [&_summary]:flex [&_summary]:list-none [&_summary]:items-center [&_summary]:justify-between [&_summary]:gap-5 [&_summary]:py-4.5 [&_summary]:text-[15px] [&_summary]:font-medium [&_summary>span]:shrink-0 [&_summary::-webkit-details-marker]:hidden">
                        {QUESTIONS.map(([q, a], index) => (
                            <div
                                key={q}
                                style={{ ["--i" as string]: index * 0.3 }}
                                className={styles.reveal}
                            >
                                <FaqItem question={q} answer={a} />
                            </div>
                        ))}
                    </div>
                </section>
            </main>

            <MeadowFooter />
        </div>
    );
}
