import { Database } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { ErpConsole } from "@/components/integracoes/erp-console";

export default function TenantErpIntegrationsPage() {
  return (
    <div className="p-6 flex flex-col gap-6">
      <PageHeader
        title="Integrações ERP"
        description="Configure o ERP conectado ao produtor, valide a comunicação e acompanhe atualização de dados, diagnóstico e pendências operacionais."
        icon={<Database className="h-5 w-5" />}
        breadcrumbs={[
          { label: "Configurações", href: "/dashboard/settings" },
          { label: "Integrações" },
          { label: "Integrações ERP" },
        ]}
      />
      <ErpConsole />
    </div>
  );
}
