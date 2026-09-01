/** @type {import('next').NextConfig} */
const API_ORIGIN = process.env.GUARDIAN_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
