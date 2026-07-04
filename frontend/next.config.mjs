/** @type {import('next').NextConfig} */
const API_BASE = process.env.MANDATE_API_BASE || "http://localhost:8000";
// Note: for Vercel production, set MANDATE_API_BASE=http://your-server:8000

const nextConfig = {
  reactStrictMode: true,
  // Proxy /api/* to the FastAPI backend so the browser only talks to the
  // frontend origin (no CORS surprises in dev or single-host deploys).
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_BASE}/api/:path*` },
      { source: "/readyz", destination: `${API_BASE}/readyz` },
      { source: "/healthz", destination: `${API_BASE}/healthz` },
      { source: "/metrics", destination: `${API_BASE}/metrics` },
    ];
  },
};

export default nextConfig;
