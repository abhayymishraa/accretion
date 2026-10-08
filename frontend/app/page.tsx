import LandingPage from "@/components/landing/LandingPage";
import { SITE_URL as BASE } from "@/config/env";
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
            "@id": `${BASE}/#organization`,
            name: "Accretion",
            url: BASE,
            logo: `${BASE}/brand/icon-512.png`,
            sameAs: ["https://github.com/abhayymishraa/accretion"],
        },
        {
            "@type": "WebSite",
            "@id": `${BASE}/#website`,
            name: "Accretion",
            url: BASE,
            publisher: { "@id": `${BASE}/#organization` },
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
