import { SITE_URL as BASE } from "@/config/env";
import type { MetadataRoute } from "next";

// Only the public pages; the app behind sign-in is disallowed in robots.ts.
export default function sitemap(): MetadataRoute.Sitemap {
    return [
        { url: BASE, changeFrequency: "weekly", priority: 1 },
        { url: `${BASE}/signup`, changeFrequency: "monthly", priority: 0.6 },
    ];
}
