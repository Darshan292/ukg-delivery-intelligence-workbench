// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // No next/image optimisation, so the optional LGPL sharp/libvips binaries are never needed.
  images: { unoptimized: true },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/:path*` },
    ];
  },
};

export default nextConfig;
