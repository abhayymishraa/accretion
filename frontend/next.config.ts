import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    reactCompiler: true,
    images: {
        // Next 16 whitelists quality values; 75 alone visibly bands the hero's
        // sky gradient, so 92 is allowed for photographic art direction.
        qualities: [75, 92],
    },
    experimental: {
        // Cached production compilations have reused the retired global stylesheet.
        turbopackFileSystemCacheForBuild: false,
    },
};

export default nextConfig;
