import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The preview is served from E2B hostnames; without this, dev assets and HMR are blocked.
  allowedDevOrigins: ["*.e2b.app", "*.e2b.dev"],
  // AGENTS.md is written by the platform; stop `next dev` from rewriting it or adding CLAUDE.md.
  agentRules: false,
};

export default nextConfig;
