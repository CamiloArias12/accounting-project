/** @type {import('next').NextConfig} */
const nextConfig = {
  // Empaqueta solo lo necesario para producción; lo usa el Dockerfile.
  output: "standalone",
};

export default nextConfig;
