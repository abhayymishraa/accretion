import { SITE_URL as BASE } from "@/config/env";
import type { MetadataRoute } from "next";

// The landing and auth pages are public; everything behind sign-in is not worth crawling. AI search crawlers are
// left allowed on purpose: blocking one removes the site from that engine's answers.
export default function robots(): MetadataRoute.Robots {
    return {
        rules: {
            userAgent: "*",
            allow: "/",
            disallow: [
                "/admin",
                "/auth",
                "/chat",
                "/connectors",
                "/profile",
                "/projects",
                "/skills",
                "/verify-email",
                "/waitlist",
            ],
        },
        sitemap: `${BASE}/sitemap.xml`,
    };
}
