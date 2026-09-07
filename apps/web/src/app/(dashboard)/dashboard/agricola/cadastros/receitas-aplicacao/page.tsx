"use client";

import { ReceitasAplicacao } from "@/components/agricola/receitas-aplicacao";
import { PageHeader } from "@/components/shared/page-header";
import { FlaskConical } from "lucide-react";

export default function ReceitasAplicacaoPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Receitas de Aplicação"
        description="Pacotes reutilizáveis de produto + dose por hectare e mão de obra padrão"
        breadcrumbs={[
          { label: "Agricultura", href: "/agricola" },
          { label: "Cadastros", href: "/agricola/cadastros" },
          { label: "Receitas de Aplicação" },
        ]}
        icon={<FlaskConical className="text-primary" size={22} />}
      />

      <ReceitasAplicacao />
    </div>
  );
}
