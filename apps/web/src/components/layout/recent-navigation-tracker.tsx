"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

const STORAGE_KEY = "agrosaas-recent-navigation";
const MAX_ITEMS = 5;

export type RecentNavigationItem = {
  href: string;
  label: string;
  visitedAt: number;
};

const LABELS: Array<[string, string]> = [
  ["/dashboard/operacional/campo/tarefas", "Tarefas de campo"],
  ["/dashboard/financeiro", "Financeiro"],
  ["/dashboard/pecuaria", "Dashboard da pecuária"],
  ["/agricola/safras", "Safras agrícolas"],
  ["/suprimentos/estoque", "Estoque"],
  ["/dashboard", "Dashboard"],
];

const SEGMENT_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  agricola: "Agrícola",
  operacional: "Operacional",
  campo: "Campo",
  frota: "Frota",
  financeiro: "Financeiro",
  pecuaria: "Pecuária",
  suprimentos: "Suprimentos",
  estoque: "Estoque",
  cadastros: "Cadastros",
  backoffice: "Backoffice",
  configuracoes: "Configurações",
};

export function getRecentNavigationLabel(pathname: string): string {
  const match = LABELS.find(([href]) => pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`)));
  if (match) return match[1];

  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return "Tela atual";

  const labels = segments.map((segment) => SEGMENT_LABELS[segment] ?? segment.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()));
  return labels.join(" · ");
}

export function RecentNavigationTracker() {
  const pathname = usePathname();

  useEffect(() => {
    if (!pathname || pathname === "/dashboard" || pathname.startsWith("/dashboard/backoffice")) return;

    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as RecentNavigationItem[];
      const next: RecentNavigationItem[] = [
        { href: pathname, label: getRecentNavigationLabel(pathname), visitedAt: Date.now() },
        ...stored.filter((item) => item.href !== pathname),
      ].slice(0, MAX_ITEMS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Storage can be unavailable in private browsing; navigation must continue normally.
    }
  }, [pathname]);

  return null;
}
