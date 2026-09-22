import { FlipWords } from "@/components/ui/flip-words";
import Image from "next/image";
import { readFileSync } from "node:fs";
import path from "node:path";
import styles from "./landing.module.css";

// WebP, not JPEG: the plate is alpha-keyed and sits under mix-blend-mode,
// so an opaque placeholder would paint a slab across transparent sky.
const plateBlur = readFileSync(
    path.join(process.cwd(), "public/brand/meadow-plate.lqip.txt"),
    "utf8",
);

// What the product can produce. Cycling these is the argument: you describe
// anything, so the headline should not name one thing.
const THINGS = ["a habit tracker", "a dashboard", "an internal tool", "a portfolio", "a shop"];

// Named because it is true of every project it writes, not because a logo row
// looked good here. Borrowed-credibility strips are the thing this replaces.
const WRITES = ["React", "Vite", "TypeScript", "Tailwind"];

export function BuildPlate() {
    return (
        <section
            id="how-it-works"
            aria-labelledby="how-it-works-heading"
            className="relative overflow-clip py-24 max-md:py-16"
        >
            {/* Crosshairs sit where the blueprint's vertical rules meet its top
                and bottom rules. */}
            <div className={styles.blueprint} aria-hidden="true">
                <span className={styles.cross} style={{ left: "15%", top: "0%" }} />
                <span className={styles.cross} style={{ left: "85%", top: "0%" }} />
                <span className={styles.cross} style={{ left: "15%", top: "100%" }} />
                <span className={styles.cross} style={{ left: "85%", top: "100%" }} />
            </div>

            <div
                style={{ ["--i" as string]: 0 }}
                className={`${styles.reveal} relative z-10 mx-auto max-w-[50rem] px-6 text-center`}
            >
                <p className="font-mono text-[11px] tracking-[0.2em] text-muted-foreground uppercase">
                    How it builds
                </p>
                <h2
                    id="how-it-works-heading"
                    className="mt-5 text-[clamp(30px,4.3vw,54px)] leading-[1.12] font-medium tracking-[-0.03em]"
                >
                    <span className="flex flex-wrap items-baseline justify-center gap-x-2">
                        <span>Describe</span>
                        {/* Absolute exit keeps the cycling word from reflowing the line. */}
                        <span className="relative inline-flex min-w-[10.5ch] justify-start">
                            <FlipWords
                                words={THINGS}
                                className="px-0 font-[family-name:var(--font-display)] italic text-accent-foreground"
                            />
                        </span>
                    </span>
                    <span className="block">and keep every line it writes.</span>
                </h2>
            </div>

            {/* The plate rises into the heading's last line, the way a printed
                specimen overlaps its caption. Sky is keyed out of the artwork,
                so the overlap crosses empty space, never the type. */}
            <figure
                style={{ ["--i" as string]: 1 }}
                className={`${styles.revealPlate} relative z-0 mx-auto -mt-8 max-w-[64rem] px-6 md:-mt-14`}
            >
                <Image
                    src="/brand/meadow-plate.png"
                    alt=""
                    aria-hidden="true"
                    width={1400}
                    height={788}
                    sizes="(max-width: 768px) 100vw, 64rem"
                    placeholder="blur"
                    blurDataURL={plateBlur}
                    className={styles.plateArt}
                />
            </figure>

            <div
                style={{ ["--i" as string]: 2 }}
                className={`${styles.reveal} relative z-10 mx-auto mt-6 max-w-[46ch] px-6 text-center`}
            >
                <p className="text-[15.5px] leading-[1.7] text-muted-foreground text-pretty">
                    Plain words in, a real project out. Accretion writes the source, installs it,
                    runs the build and shows you the running app.
                </p>
            </div>

            <div className="relative mx-auto mt-14 flex max-w-[56rem] flex-wrap items-center justify-center gap-x-9 gap-y-3 border-t border-border px-6 pt-6">
                <p
                    style={{ ["--i" as string]: 3 }}
                    className={`${styles.reveal} font-mono text-[11px] tracking-[0.18em] text-muted-foreground uppercase`}
                >
                    What it writes
                </p>
                {WRITES.map((name, index) => (
                    <span
                        key={name}
                        style={{ ["--i" as string]: 3.3 + index * 0.3 }}
                        className={`${styles.reveal} text-[15px] font-medium tracking-[-0.01em] text-foreground/55`}
                    >
                        {name}
                    </span>
                ))}
            </div>
        </section>
    );
}
