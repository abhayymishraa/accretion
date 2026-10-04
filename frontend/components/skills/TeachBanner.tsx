import { MessageSquareText, PenLine, Sparkles } from "lucide-react";
import { OrbitFigure } from "./OrbitFigure";
import styles from "./skills.module.css";

const STEPS = [
    {
        icon: PenLine,
        title: "Add a skill",
        body: "Write one yourself, import a .md or .zip file, or bring them in from GitHub.",
    },
    {
        icon: Sparkles,
        title: "Build like usual",
        body: "When a request matches a skill, Accretion uses it on its own.",
    },
    {
        icon: MessageSquareText,
        title: "Call one by name",
        body: "Type / and the skill's name in chat to use it on purpose.",
        chip: "/brand-voice",
    },
] as const;

/** The introduction at the top of the library, always shown. */
export function TeachBanner() {
    return (
        <section aria-labelledby="teach-title" className="mb-10">
            <div className="grid gap-px border border-border bg-border md:grid-cols-[minmax(0,1fr)_240px]">
                <div className="flex flex-col bg-background">
                    <h2
                        id="teach-title"
                        className="px-5 pt-5 pb-4 text-[22px] leading-[1.25] font-medium tracking-[-0.4px] text-balance"
                    >
                        Teach Accretion how you work.
                    </h2>
                    <ol
                        className={`${styles.grain} grid flex-1 gap-px border-t border-border bg-border`}
                    >
                        {STEPS.map((step) => (
                            <li key={step.title} className="flex gap-3 bg-background/92 px-5 py-3">
                                <step.icon
                                    size={16}
                                    strokeWidth={1.75}
                                    className="mt-0.5 shrink-0 text-primary"
                                    aria-hidden="true"
                                />
                                <div className="min-w-0">
                                    <h3 className="text-[14px] font-medium">{step.title}</h3>
                                    <p className="mt-0.5 text-[13px] leading-[1.5] text-muted-foreground">
                                        {step.body}
                                    </p>
                                    {"chip" in step && (
                                        <code
                                            className={`${styles.chip} mt-1.5 inline-block px-1.5 py-0.5 font-mono text-[11.5px] leading-none`}
                                        >
                                            {step.chip}
                                        </code>
                                    )}
                                </div>
                            </li>
                        ))}
                    </ol>
                </div>
                <div className="flex items-center bg-background px-5 py-5 max-md:order-first">
                    <OrbitFigure />
                </div>
            </div>
        </section>
    );
}
