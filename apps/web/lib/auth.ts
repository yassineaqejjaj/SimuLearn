"use client";
import Keycloak from "keycloak-js";

const MODE = process.env.NEXT_PUBLIC_AUTH_MODE ?? "keycloak"; // "dev" uniquement en développement local
const KEY = "simulearn.dev-token";
let kc: Keycloak | null = null;

export const authMode = MODE;

export async function initAuth(): Promise<boolean> {
  if (MODE === "dev") return !!localStorage.getItem(KEY);
  kc = new Keycloak({
    url: process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "", realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "",
    clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "",
  });
  return kc.init({ onLoad: "check-sso", pkceMethod: "S256" });
}

export function devLogin(email: string, role: "learner" | "trainer") {
  localStorage.setItem(KEY, `dev:${email}:${role}`);
}

export function login() { if (kc) void kc.login(); }

export function logout() {
  if (MODE === "dev") { localStorage.removeItem(KEY); location.href = "/login"; return; }
  void kc?.logout({ redirectUri: location.origin });
}

export async function getToken(): Promise<string | null> {
  if (MODE === "dev") return localStorage.getItem(KEY);
  if (!kc?.authenticated) return null;
  await kc.updateToken(30).catch(() => kc?.login());
  return kc.token ?? null;
}

export function isTrainerDev(): boolean {
  return MODE === "dev" && (localStorage.getItem(KEY) ?? "").endsWith(":trainer");
}
export function isTrainer(): boolean {
  if (MODE === "dev") return isTrainerDev();
  const roles = (kc?.tokenParsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? [];
  return roles.includes("trainer") || roles.includes("admin");
}
