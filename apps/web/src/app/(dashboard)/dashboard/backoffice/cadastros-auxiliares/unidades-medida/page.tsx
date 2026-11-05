"use client";

import { UomReusable } from "@/components/cadastros/tabelas-reusable/uom-reusable";
import { PageHeader } from "@/components/shared/page-header";
import { Ruler } from "lucide-react";

export default function BackofficeUnidadesMedidaPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Unidades de Medida"
        description="Gerencie as unidades de medida globais disponíveis para todos os assinantes"
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Tabelas do Sistema", href: "/dashboard/backoffice/tabelas" },
          { label: "Unidades de Medida" },
        ]}
        icon={<Ruler className="text-primary" size={22} />}
      />

      <UomReusable />
    </div>
  );
}
