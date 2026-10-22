import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  redirects: async () => [
    { source: "/history", destination: "/progression#historique", permanent: false },
    { source: "/compare", destination: "/progression", permanent: false },
  ],
};
export default config;
