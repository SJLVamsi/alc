/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  rewrites: async () => [
    { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' },
  ],
}

module.exports = nextConfig
