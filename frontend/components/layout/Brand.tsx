import Link from "next/link";

export function Brand() {
    return (
        <Link
            href="/"
            className="ember-brand inline-flex items-center gap-2.5 font-brand text-foreground text-[23px] font-semibold tracking-[-0.9px] whitespace-nowrap no-underline [&>svg]:text-accent-foreground [&>svg]:shrink-0 [&>svg]:h-auto max-md:text-[21px]"
            aria-label="Accretion home"
        >
            <svg viewBox="0 0 100 100" width={30} height={30} aria-hidden="true" focusable="false">
                <use href="/brand/accretion-mark.svg#mark" />
            </svg>
            <span>accretion</span>
        </Link>
    );
}
