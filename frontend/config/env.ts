export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// No trailing slash, so robots, the sitemap and JSON-LD can append paths with one "/".
export const SITE_URL = (process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000").replace(
    /\/+$/,
    "",
);
