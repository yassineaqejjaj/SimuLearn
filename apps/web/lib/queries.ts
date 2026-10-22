"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { Me, Scenario, SessionInfo } from "./types";

export const useScenarios = () => useQuery({ queryKey: ["scenarios"], queryFn: () => api<Scenario[]>("/api/scenarios") });
export const useHistory = () => useQuery({ queryKey: ["history"], queryFn: () => api<SessionInfo[]>("/api/simulations") });
export const useMe = () => useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/api/me") });
