import { SITE_URL } from "@/config/env";
import type { MetadataRoute } from "next";

// Only the public pages; the app behind sign-in is disallowed in robots.ts.
export default function sitemap(): MetadataRoute.Sitemap {
    return [{ url: SITE_URL }, { url: `${SITE_URL}/signup` }];
}
