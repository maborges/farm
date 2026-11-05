"use client";

import { CulturasReusable } from "@/components/cadastros/tabelas-reusable/culturas-reusable";
import { PageHeader } from "@/components/shared/page-header";
import { Sprout } from "lucide-react";

export default function BackofficeCulturasPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Culturas do Sistema"
        description="Gerencie as culturas e parâmetros agronômicos disponíveis para todos os assinantes"
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Tabelas do Sistema", href: "/dashboard/backoffice/tabelas" },
          { label: "Culturas" }
        ]}
        icon={<Sprout className="text-primary" size={22} />}
      />

      <CulturasReusable mode="backoffice" />
    </div>
  );
}
