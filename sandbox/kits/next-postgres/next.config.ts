import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The preview is served from E2B hostnames; without this, dev assets and HMR are blocked.
  allowedDevOrigins: ["*.e2b.app", "*.e2b.dev"],
  // The platform keeps the project notes in .accretion/; stop `next dev` from writing AGENTS.md or CLAUDE.md.
  agentRules: false,
};

export default nextConfig;
