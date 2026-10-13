import type { NextConfig } from 'next';

const config: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  experimental: { proxyClientMaxBodySize: 26_000_000 },
  async rewrites() {
    return process.env.NEXT_PUBLIC_API_MODE === 'live'
      ? [{ source: '/api/v1/:path*', destination: `${process.env.API_ORIGIN ?? 'http://127.0.0.1:8000'}/api/v1/:path*` }]
      : [];
  },
};
export default config;
