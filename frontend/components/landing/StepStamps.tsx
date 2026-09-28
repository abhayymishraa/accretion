import { buttonVariants } from "@/components/ui/button";
import { ArrowUpRight } from "lucide-react";
import { readFileSync } from "node:fs";
import path from "node:path";
import Image from "next/image";
import Link from "next/link";
import styles from "./landing.module.css";

// Read once at module scope; every component on this page is a server component.
const lqip = (name: string) =>
    readFileSync(path.join(process.cwd(), `public/brand/${name}.lqip.txt`), "utf8");

// artFirst flips the middle stamp so the sheet reads as three printings of one
// plate rather than three copies of one card.
const STEPS = [
    {
        n: "01",
        title: "Describe it in plain words.",
        body: "No spec, no scaffolding, no setup screen to fill in first.",
        art: "/brand/stamp-describe.png",
        blur: lqip("stamp-describe"),
        artFirst: false,
    },
    {
        n: "02",
        title: "It writes it and runs the build.",
        body: "Source, install, build, preview. You watch each step as it happens.",
        art: "/brand/stamp-build.png",
        blur: lqip("stamp-build"),
        artFirst: true,
    },
    {
        n: "03",
        title: "Keep every line of it.",
        body: "Read each file, download the project, run it anywhere you like.",
        art: "/brand/stamp-keep.png",
        blur: lqip("stamp-keep"),
        artFirst: false,
    },
] as const;

export function StepStamps() {
    return (
        <section
            id="steps"
            aria-labelledby="steps-heading"
            className={`${styles.ruleTop} py-24 max-md:py-16`}
        >
            <h2
                id="steps-heading"
                style={{ ["--i" as string]: 0 }}
                className={`${styles.reveal} mx-auto max-w-[20ch] text-center text-[clamp(26px,3vw,38px)] leading-[1.15] font-medium tracking-[-0.03em] text-balance`}
            >
                Three printings, one plate.
            </h2>

            <ul className="mx-auto mt-12 grid max-w-[64rem] grid-cols-3 gap-7 px-6 max-md:grid-cols-1 max-md:max-w-[26rem]">
                {STEPS.map(({ n, title, body, art, blur, artFirst }, index) => (
                    <li
                        key={n}
                        style={{ ["--i" as string]: index + 1 }}
                        className={`${styles.stampWrap} ${styles.reveal}`}
                    >
                        <article
                            className={`${styles.stamp} flex h-[27rem] flex-col ${
                                artFirst ? "flex-col-reverse" : ""
                            }`}
                        >
                            <div className="flex flex-1 flex-col justify-between p-6 text-[#10212f]">
                                {/* The card arrives, then its mark and number
                                    settle into it a beat later. */}
                                <div
                                    style={{ ["--i" as string]: index + 1.4 }}
                                    className={`${styles.reveal} flex items-center justify-between ${
                                        artFirst ? "order-2" : "order-1"
                                    }`}
                                >
                                    <svg
                                        viewBox="0 0 100 100"
                                        width={19}
                                        height={19}
                                        aria-hidden="true"
                                        focusable="false"
                                    >
                                        <use href="/brand/accretion-mark-mono.svg#mark" />
                                    </svg>
                                    <span className="font-mono text-[13px] tracking-[0.04em]">
                                        {n}
                                    </span>
                                </div>
                                <div className={artFirst ? "order-1" : "order-2"}>
                                    <h3 className="max-w-[16ch] text-[19px] leading-[1.25] font-medium tracking-[-0.02em] text-balance">
                                        {title}
                                    </h3>
                                    <p className="mt-2 max-w-[30ch] text-[13px] leading-[1.65] text-[#10212f]/65 text-pretty">
                                        {body}
                                    </p>
                                </div>
                            </div>
                            <div className="h-[45%] overflow-hidden">
                                <Image
                                    src={art}
                                    alt=""
                                    aria-hidden="true"
                                    width={660}
                                    height={452}
                                    sizes="(max-width: 768px) 92vw, 21rem"
                                    placeholder="blur"
                                    blurDataURL={blur}
                                    className={styles.stampArt}
                                />
                            </div>
                        </article>
                    </li>
                ))}
            </ul>

            <div className="mt-12 flex justify-center px-6">
                <Link
                    href="/chat"
                    className={buttonVariants({
                        variant: "outlinePill",
                        className: "group h-12 pr-2 pl-6 text-[14.5px]",
                    })}
                >
                    Start building
                    <span className="flex size-9 items-center justify-center rounded-full bg-foreground/10 transition-transform duration-[160ms] ease-[var(--ease-out)] pointer-fine:group-hover:-translate-y-px pointer-fine:group-hover:translate-x-[2px]">
                        <ArrowUpRight size={16} aria-hidden="true" />
                    </span>
                </Link>
            </div>
        </section>
    );
}
