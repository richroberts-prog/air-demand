/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Use standalone output for Docker deployments
  // This creates a minimal server.js for production
  output: process.env.NEXT_OUTPUT_MODE || 'standalone',

  // Note: rewrites don't work with static export
  // In development, use API routes proxy
  // In production, dashboard calls API directly via NEXT_PUBLIC_API_URL
}

module.exports = nextConfig
