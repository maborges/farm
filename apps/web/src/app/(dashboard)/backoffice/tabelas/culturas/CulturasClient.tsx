"use client";

import { CulturasReusable } from "@/components/cadastros/tabelas-reusable/culturas-reusable";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Sprout } from "lucide-react";
import Link from "next/link";

export function CulturasClient() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/backoffice/tabelas">
          <Button variant="outline" size="sm" className="size-8 rounded-sm">
            <ArrowLeft className="size-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-semibold">Culturas do Sistema</h1>
          <p className="text-sm text-muted-foreground">
            Gerencie as culturas globais disponíveis para todos os tenants
          </p>
        </div>
      </div>

      <CulturasReusable mode="backoffice" />
    </div>
  );
}
