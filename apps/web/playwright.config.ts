import { defineConfig } from "@playwright/test";

// Prérequis : API en mode mock (infrastructure/scripts/dev.sh). Aucun appel payant.
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000", channel: "chrome" }, // Chrome installé : aucun téléchargement de navigateur
});
