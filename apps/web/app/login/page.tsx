"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Logo } from "@/components/Shell";
import { Button, Card } from "@/components/ui";
import { authMode, devLogin, login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("etudiant@ifsi-demo.test");
  const [role, setRole] = useState<"learner" | "trainer">("learner");
  return (
    <main className="grid min-h-screen place-items-center bg-night px-4">
      <Card className="w-full max-w-md">
        <h1><Logo /></h1>
        <p className="mt-1 text-sm text-slate">Practice before it matters.</p>
        {authMode === "dev" ? (
          <form className="mt-6 space-y-4" onSubmit={(e) => { e.preventDefault(); devLogin(email, role); router.push(role === "trainer" ? "/trainer" : "/"); }}>
            <p className="rounded-xl bg-amber-soft p-3 text-sm text-amber-ink">Mode de développement : connexion simulée, sans Keycloak. Ne jamais utiliser en production.</p>
            <label className="block text-sm font-medium">Adresse e-mail
              <input className="mt-1 w-full rounded-xl border border-[#CBD5E1] p-2" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label className="block text-sm font-medium">Rôle
              <select className="mt-1 w-full rounded-xl border border-[#CBD5E1] p-2" value={role} onChange={(e) => setRole(e.target.value as "learner" | "trainer")}>
                <option value="learner">Apprenant</option><option value="trainer">Formateur</option>
              </select>
            </label>
            <Button type="submit" className="w-full">Se connecter</Button>
          </form>
        ) : (
          <Button className="mt-6 w-full" onClick={login}>Se connecter avec Keycloak</Button>
        )}
        <p className="mt-4 text-xs text-slate">Les conversations sont traitées par OpenAI (voix) et Anthropic (évaluation). Aucun enregistrement audio n'est conservé. Utilisez uniquement des situations fictives.</p>
      </Card>
    </main>
  );
}
