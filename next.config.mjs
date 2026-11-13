// Single Vercel project: Next.js (Mini App "/", admin "/admin") + Python FastAPI function in api/index.py.
// In production the API paths go to that function; locally (next dev) they are proxied to API_URL.
const dev = process.env.NODE_ENV === "development";
const API = process.env.API_URL || "http://127.0.0.1:8000";
const sources = ["/api/v1/:path*", "/internal/:path*", "/health"];
export default {
  reactStrictMode: true,
  async rewrites() {
    return { beforeFiles: sources.map((source) => ({ source, destination: dev ? `${API}${source}` : "/api/" })) };
  },
};
