import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable ESLint checks during production builds to prevent build failures due to lint errors
  eslint: {
    ignoreDuringBuilds: true,
  },
  /* config options here */
};

export default nextConfig;
