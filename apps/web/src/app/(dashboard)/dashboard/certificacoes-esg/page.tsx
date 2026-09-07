import { ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { CertificacoesEsgClient } from "./CertificacoesEsgClient";

export default function CertificacoesEsgPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Certificações & ESG"
        description="Visão operacional do domínio consumidor com evidências, não conformidades e planos de ação."
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Certificações & ESG" },
        ]}
        icon={<ShieldCheck className="size-5" />}
      />
      <CertificacoesEsgClient />
    </div>
  );
}
