"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Density, PageKey, Role } from "@/types/fabriguard";

interface UiState {
  role: Role;
  page: PageKey;
  useMock: boolean;
  density: Density;
  search: string;
  setRole: (role: Role) => void;
  setPage: (page: PageKey) => void;
  setUseMock: (useMock: boolean) => void;
  setDensity: (density: Density) => void;
  setSearch: (search: string) => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      role: "operator",
      page: "dashboard",
      useMock: false,
      density: "compact",
      search: "",
      setRole: (role) => set({ role, page: "dashboard" }),
      setPage: (page) => set({ page }),
      setUseMock: (useMock) => set({ useMock }),
      setDensity: (density) => set({ density }),
      setSearch: (search) => set({ search }),
    }),
    { name: "fabriguard-ui" },
  ),
);
