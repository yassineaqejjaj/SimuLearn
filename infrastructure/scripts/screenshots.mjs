// Captures d'écran du README. Prérequis : API + web en mode mock (dev.sh) et demo_data.py exécuté.
// Utilise le Chrome installé (aucun navigateur à télécharger). Usage : node infrastructure/scripts/screenshots.mjs
import { fileURLToPath } from "node:url";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const WEB = process.env.WEB_URL ?? "http://localhost:3000";
const API = process.env.API_URL ?? "http://127.0.0.1:8000";
const OUT = fileURLToPath(new URL("../../docs/screenshots/", import.meta.url));
const auth = (email, role) => `dev:${email}:${role}`;

const api = async (path, token) => (await fetch(API + path, { headers: { Authorization: `Bearer ${token}` } })).json();
const browser = await chromium.launch({ channel: "chrome" });

async function session(role, email, viewport = { width: 1440, height: 900 }) {
  const ctx = await browser.newContext({ viewport, locale: "fr-FR", reducedMotion: "reduce" });
  await ctx.addInitScript((t) => localStorage.setItem("simulearn.dev-token", t), auth(email, role));
  return ctx.newPage();
}
const shot = async (page, name, full = false) => { await page.waitForTimeout(600); await page.screenshot({ path: `${OUT}${name}.png`, fullPage: full }); console.log("✓", name); };

const learner = await session("learner", "camille.dubois@ifsi-demo.test");
const scenarios = await api("/api/scenarios", auth("camille.dubois@ifsi-demo.test", "learner"));
const marc = scenarios.find((s) => s.character.name === "Marc Laurent");
const history = await api("/api/simulations", auth("camille.dubois@ifsi-demo.test", "learner"));
const lastDone = history.find((h) => h.status === "COMPLETED");

await learner.goto(`${WEB}/`); await learner.getByRole("heading", { name: /prêt à vous entraîner/ }).waitFor(); await shot(learner, "01-tableau-de-bord", true);
await learner.goto(`${WEB}/catalogue`); await learner.getByRole("heading", { name: "Simulations" }).waitFor(); await shot(learner, "02-catalogue");
await learner.goto(`${WEB}/scenarios/${marc.id}`); await learner.getByRole("heading", { name: marc.title }).waitFor(); await shot(learner, "03-detail-scenario", true);
await learner.goto(`${WEB}/preparation/${marc.id}`); await learner.getByRole("button", { name: "Démarrer la simulation" }).waitFor(); await shot(learner, "04-preparation");

// Salle : une vraie conversation en mode texte (mock)
await learner.getByRole("button", { name: "Démarrer la simulation" }).click();
let turnIndex = 0;
const box = learner.getByPlaceholder("Ce que vous diriez au patient…"); await box.waitFor();
for (const t of ["Bonjour monsieur Laurent, je suis étudiant infirmier et je vais m'occuper de vous.", "Je comprends que cette attente vous inquiète, vous attendez depuis longtemps sans explication."]) {
  await box.fill(t); await box.press("Enter"); await learner.getByText(t).first().waitFor();
  await learner.locator("aside").getByText("Marc Laurent ·").nth(turnIndex++).waitFor(); // réponse du patient reçue
}
await learner.waitForTimeout(500); await shot(learner, "05-salle-simulation");
await learner.getByRole("button", { name: "Terminer la simulation" }).click();
await shot(learner, "06-fin-de-session");
await learner.getByRole("button", { name: "Terminer et consulter mes résultats" }).click();
await learner.getByRole("heading", { name: "Vos compétences" }).waitFor({ timeout: 20000 }); await shot(learner, "07-resultats", true);

await learner.goto(`${WEB}/progression`); await learner.getByRole("heading", { name: "Comparer deux tentatives" }).waitFor(); await shot(learner, "08-progression", true);

// Mobile : salle
const phone = await session("learner", "camille.dubois@ifsi-demo.test", { width: 390, height: 844 });
await phone.goto(`${WEB}/preparation/${marc.id}`); await phone.getByRole("button", { name: "Démarrer la simulation" }).click();
await phone.getByPlaceholder("Ce que vous diriez au patient…").waitFor(); await shot(phone, "09-salle-mobile");

// Formateur
const trainer = await session("trainer", "formateur@ifsi-demo.test");
await trainer.goto(`${WEB}/trainer`); await trainer.getByRole("heading", { name: "Espace formateur" }).waitFor(); await shot(trainer, "10-formateur-tableau-de-bord", true);
const row = (await api("/api/trainer/sessions", auth("formateur@ifsi-demo.test", "trainer"))).find((s) => s.evaluation_id);
await trainer.goto(`${WEB}/trainer/evaluations/${row.evaluation_id}`); await trainer.getByRole("heading", { name: "Examen de l'évaluation" }).waitFor(); await shot(trainer, "11-formateur-relecture");
await browser.close();
