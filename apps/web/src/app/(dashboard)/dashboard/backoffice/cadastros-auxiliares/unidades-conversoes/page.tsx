"use client";

import { UomConversoesReusable } from "@/components/cadastros/tabelas-reusable/uom-conversoes-reusable";
import { PageHeader } from "@/components/shared/page-header";
import { ArrowLeftRight } from "lucide-react";

export default function BackofficeUnidadesConversoesPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Conversões de Unidade"
        description="Gerencie os fatores de conversão entre unidades de medida globais"
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Tabelas do Sistema", href: "/dashboard/backoffice/tabelas" },
          { label: "Conversões de Unidade" },
        ]}
        icon={<ArrowLeftRight className="text-primary" size={22} />}
      />

      <UomConversoesReusable />
    </div>
  );
}
