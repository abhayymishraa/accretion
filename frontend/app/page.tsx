import LandingPage from "@/components/landing/LandingPage";
import { SITE_URL } from "@/config/env";
import type { Metadata } from "next";

// The landing page carries the descriptive title search results show; app pages keep their own short titles.
export const metadata: Metadata = {
    title: "Accretion: describe an app, review the plan, get it built",
    alternates: { canonical: "/" },
};

// Who publishes the site and what it is called, for search results. Server-rendered, so crawlers read it
// without running JavaScript.
const STRUCTURED_DATA = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Organization",
            "@id": `${SITE_URL}/#organization`,
            name: "Accretion",
            url: SITE_URL,
            logo: `${SITE_URL}/brand/icon-512.png`,
            sameAs: ["https://github.com/abhayymishraa/accretion"],
        },
        {
            "@type": "WebSite",
            "@id": `${SITE_URL}/#website`,
            name: "Accretion",
            url: SITE_URL,
            publisher: { "@id": `${SITE_URL}/#organization` },
        },
    ],
};

export default function Page() {
    return (
        <>
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{ __html: JSON.stringify(STRUCTURED_DATA) }}
            />
            <LandingPage />
        </>
    );
}
