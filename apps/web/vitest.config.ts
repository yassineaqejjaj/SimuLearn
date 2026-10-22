import { defineConfig } from "vitest/config";

// Les tests de bout en bout (e2e/) sont exécutés par Playwright, pas par Vitest.
export default defineConfig({ test: { include: ["lib/**/*.test.ts"], exclude: ["e2e/**", "node_modules/**"] } });
