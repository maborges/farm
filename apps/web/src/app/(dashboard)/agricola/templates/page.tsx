"use client";

import { PageHeader } from "@/components/shared/page-header";
import { AgroTemplatesManager } from "@/components/agricola/agro-templates-manager";
import { LayoutTemplate } from "lucide-react";

export default function AgroTemplatesPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Templates de Operação"
        description="Modelos reutilizáveis de checklist, tarefas e planos de ação para suas safras. Templates globais do sistema são somente leitura — crie os seus próprios para customizar."
        breadcrumbs={[
          { label: "Agricultura", href: "/agricola" },
          { label: "Templates de Operação" },
        ]}
        icon={<LayoutTemplate className="text-primary" size={22} />}
      />

      <AgroTemplatesManager />
    </div>
  );
}
