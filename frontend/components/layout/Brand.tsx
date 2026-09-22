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

export function EmberArtwork() {
    return (
        <figure
            className="ember-art [&_figcaption]:text-[13px] [&_figcaption]:leading-[1.6]"
            aria-label="Make your next move"
        >
            <div className="ember-art-top flex justify-between items-center gap-5 text-[10px] [&>span:first-child]:font-brand [&>span:first-child]:text-[16px] [&>span:first-child]:tracking-[-0.5px] [&>span:first-child]:font-semibold">
                <span>accretion</span>
                <span>From idea to interface</span>
            </div>
            <p className="ember-art-title text-[clamp(44px,_4.6vw,_70px)] tracking-[-0.055em] font-medium leading-[1.03] my-[45px]">
                Make your
                <br />
                next move.
            </p>
            <figcaption>
                Direct. Confident.
                <br />
                Ready to build.
            </figcaption>
        </figure>
    );
}
