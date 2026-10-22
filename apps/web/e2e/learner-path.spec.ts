import { expect, test } from "@playwright/test";

// Parcours apprenant en mode MOCK (texte, aucune API distante). Ne valide pas la voix réelle.
test("connexion, préparation, simulation, résultats, nouvelle tentative, comparaison", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Se connecter" }).click();
  const turns = ["Bonjour monsieur Laurent, je suis étudiant infirmier.", "Je comprends que cette attente vous inquiète.", "L'équipe va vous informer dans quelques minutes."];
  for (let attempt = 0; attempt < 2; attempt++) {
    await page.goto("/catalogue");
    await page.getByRole("link", { name: /Commencer|Recommencer/ }).first().click();
    await page.getByRole("link", { name: "Se préparer" }).click();
    await page.getByRole("button", { name: "Démarrer la simulation" }).click();
    for (const t of turns) {
      await page.getByPlaceholder("Ce que vous diriez au patient…").fill(t);
      await page.keyboard.press("Enter");
      await expect(page.getByText(t).first()).toBeVisible();
    }
    await page.getByRole("button", { name: "Terminer la simulation" }).click();
    await page.getByRole("button", { name: "Terminer et consulter mes résultats" }).click();
    await expect(page.getByRole("heading", { name: "Votre simulation est terminée" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Vos compétences" })).toBeVisible({ timeout: 15000 });
  }
  await page.goto("/progression");
  await expect(page.getByRole("heading", { name: "Comparer deux tentatives" })).toBeVisible();
  await expect(page.getByRole("table", { name: /Évolution des scores/ })).toBeVisible();
});
