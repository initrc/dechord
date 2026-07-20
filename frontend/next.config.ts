import type { NextConfig } from "next"

const backendUrl = process.env.API_BASE_URL ?? "http://localhost:8000"

const nextConfig: NextConfig = {
    async rewrites() {
        return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }]
    },
}

export default nextConfig
