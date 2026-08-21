import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    // Pin the workspace root to this app. Without it Next infers the home
    // directory (stray lockfile) and module idents include the non-ASCII
    // parent path, which crashes Turbopack (char-boundary panic).
    root: __dirname,
  },
};

export default nextConfig;
