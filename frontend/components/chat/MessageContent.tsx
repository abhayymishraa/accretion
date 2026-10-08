"use client";

import { Streamdown } from "streamdown";

// Replies are markdown. Streamdown sanitizes raw HTML and copes with unfinished markdown; the overrides
// keep headings chat-sized instead of document-sized.
export function MessageContent({
    content,
    className = "",
}: {
    content: string;
    className?: string;
}) {
    return (
        <Streamdown
            mode="static"
            linkSafety={{ enabled: false }}
            className={`mt-3 text-[14.5px] leading-[1.7] wrap-anywhere text-pretty max-[481px]:text-[14px] [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_:is(h1,h2,h3,h4)]:mt-6 [&_:is(h1,h2,h3,h4)]:mb-1.5 [&_:is(h1,h2,h3,h4)]:text-[15px] [&_:is(h1,h2,h3,h4)]:font-semibold [&_p]:my-3 [&_:is(ul,ol)]:my-3.5 [&_:is(ul,ol)]:list-outside [&_:is(ul,ol)]:pl-5 [&_li]:my-2 [&_li]:pl-1 [&_li]:py-0 [&_li]:marker:text-muted-foreground [&_strong]:font-semibold [&_strong]:text-foreground [&_a]:underline [&_a]:underline-offset-2 [&_:not(pre)>code]:rounded-[4px] [&_:not(pre)>code]:bg-surface-3 [&_:not(pre)>code]:px-1 [&_:not(pre)>code]:py-0.5 [&_:not(pre)>code]:font-mono [&_:not(pre)>code]:text-[0.88em] ${className}`}
        >
            {content}
        </Streamdown>
    );
}
