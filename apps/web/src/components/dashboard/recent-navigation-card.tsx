"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Clock3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { RecentNavigationItem } from "@/components/layout/recent-navigation-tracker";

const STORAGE_KEY = "agrosaas-recent-navigation";

export function RecentNavigationCard() {
  const [items, setItems] = useState<RecentNavigationItem[]>([]);

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as RecentNavigationItem[];
      setItems(stored.filter((item) => item.href !== "/dashboard").slice(0, 3));
    } catch {
      setItems([]);
    }
  }, []);

  if (items.length === 0) return null;

  return (
    <section className="rounded-sm border bg-card p-4 shadow-sm" aria-labelledby="recent-navigation-title">
      <div className="mb-3 flex items-center gap-2">
        <Clock3 className="size-4 text-primary" aria-hidden="true" />
        <div>
          <h2 id="recent-navigation-title" className="text-sm font-semibold">Continuar de onde parou</h2>
          <p className="text-xs text-muted-foreground">Acesse rapidamente as últimas telas visitadas.</p>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        {items.map((item) => (
          <Button key={item.href} asChild variant="outline" className="h-auto min-h-10 justify-between gap-2 px-3 py-2 text-left">
            <Link href={item.href}>
              <span className="truncate text-xs font-medium">{item.label}</span>
              <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
            </Link>
          </Button>
        ))}
      </div>
    </section>
  );
}

