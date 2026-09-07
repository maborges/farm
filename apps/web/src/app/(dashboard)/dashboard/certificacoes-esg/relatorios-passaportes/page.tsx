import { Metadata } from "next";
import { FileText } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { RelatoriosPassaportesClient } from "./RelatoriosPassaportesClient";

export const metadata: Metadata = {
  title: "Relatórios ESG & Passaportes | AgroSaaS",
  description: "Gestão de Relatórios ESG e Passaportes de Rastreabilidade",
};

export default async function RelatoriosPassaportesPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Relatórios & Passaportes"
        description="Acompanhamento de relatórios ESG e emissão de passaportes de rastreabilidade"
        icon={<FileText className="size-5" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Certificações & ESG", href: "/dashboard/certificacoes-esg" },
          { label: "Relatórios & Passaportes" },
        ]}
      />
      <RelatoriosPassaportesClient />
    </div>
  );
}
