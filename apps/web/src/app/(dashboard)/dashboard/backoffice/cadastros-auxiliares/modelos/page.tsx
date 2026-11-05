"use client";
import { ModelosReusable } from "@/components/cadastros/tabelas-reusable/modelos-reusable";
import { PageHeader } from "@/components/shared/page-header";
import { Layers } from "lucide-react";

export default function ModelosBackofficePage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Modelos de Produto"
        description="Gerencie os modelos e referências globais vinculados às marcas"
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Tabelas do Sistema", href: "/dashboard/backoffice/tabelas" },
          { label: "Modelos" }
        ]}
        icon={<Layers className="text-primary" size={22} />}
      />
      <ModelosReusable mode="backoffice" />
    </div>
  );
}
