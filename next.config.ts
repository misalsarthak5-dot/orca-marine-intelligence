import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: '/ask-orca',
        destination: '/ask',
        permanent: true,
      },
      {
        source: '/live-marine-map',
        destination: '/live-map',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
