import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "@/components/Shell";

const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = { title: "SimuLearn — Practice before it matters", description: "Simulations professionnelles vocales pour la formation en santé." };

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="fr" className={inter.variable}><body className="font-sans"><Providers>{children}</Providers></body></html>;
}
