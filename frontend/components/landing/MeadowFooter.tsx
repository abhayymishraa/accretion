import { Brand } from "@/components/layout/Brand";
import { readFileSync } from "node:fs";
import Image from "next/image";
import Link from "next/link";
import path from "node:path";
import styles from "./landing.module.css";

const ART = "/brand/meadow-source.png";
const blurDataURL = readFileSync(path.join(process.cwd(), "public/brand/meadow.lqip.txt"), "utf8");

const COLUMNS = [
    [
        "Product",
        [
            ["How it works", "#how-it-works"],
            ["Questions", "#faq"],
        ],
    ],
    [
        "Build",
        [
            ["Start a project", "/chat"],
            ["Your projects", "/projects"],
        ],
    ],
    [
        "Account",
        [
            ["Sign in", "/signin"],
            ["Create account", "/signup"],
            ["Profile", "/profile"],
        ],
    ],
    ["More", [["GitHub", "https://github.com/abhayymishraa/accretion"]]],
] as const;

export function MeadowFooter() {
    return (
        <footer className="relative isolate mt-10 overflow-clip" aria-labelledby="footer-heading">
            <h2 id="footer-heading" className="sr-only">
                Accretion
            </h2>

            <Image
                src={ART}
                alt=""
                aria-hidden="true"
                fill
                quality={92}
                sizes="100vw"
                placeholder="blur"
                blurDataURL={blurDataURL}
                className={styles.footerArt}
            />
            <div className={styles.footerVeil} aria-hidden="true" />
            <span className={styles.ghostMark} aria-hidden="true">
                accretion
            </span>

            <div className="mx-auto w-full max-w-[72rem] px-6 pt-16 pb-[26rem] max-md:pb-[20rem]">
                <div className="grid grid-cols-[1.4fr_repeat(4,minmax(0,1fr))] gap-10 max-[900px]:grid-cols-2 max-md:gap-8">
                    <div
                        style={{ ["--i" as string]: 0 }}
                        className={`${styles.reveal} max-[900px]:col-span-2 [&_.ember-brand]:gap-2.5 [&_.ember-brand]:text-[21px] [&_.ember-brand>svg]:w-[24px] [&_.ember-brand]:transition-opacity [&_.ember-brand]:duration-150 pointer-fine:[&_.ember-brand:hover]:opacity-80`}
                    >
                        <Brand />
                        <p className="mt-2 max-w-[26ch] text-[13.5px] leading-relaxed text-foreground/75">
                            Describe an app. Keep every line of code.
                        </p>
                        <p className="mt-6 text-[12.5px] text-muted-foreground">
                            © {new Date().getFullYear()} Accretion. All rights reserved.
                        </p>
                    </div>

                    {COLUMNS.map(([heading, links], index) => (
                        <nav
                            key={heading}
                            aria-label={heading}
                            style={{ ["--i" as string]: 0.3 + index * 0.3 }}
                            className={styles.reveal}
                        >
                            <p className="text-[13px] font-semibold">{heading}</p>
                            <ul className="mt-3 space-y-2.5">
                                {links.map(([label, href]) => (
                                    <li key={label}>
                                        <Link
                                            href={href}
                                            className="text-[13px] text-foreground/70 transition-colors duration-150 ease-out pointer-fine:hover:text-foreground"
                                        >
                                            {label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </nav>
                    ))}
                </div>
            </div>
        </footer>
    );
}
