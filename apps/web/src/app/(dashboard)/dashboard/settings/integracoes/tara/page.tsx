import { Scale } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { TaraConsole } from "@/components/balanca/tara-console";

export default function TaraSettingsPage() {
  return (
    <div className="p-6 flex flex-col gap-6">
      <PageHeader
        title="Tara-Balança"
        description="Atualize os dados de conexão e valide a integração com a Plataforma TARA."
        icon={<Scale className="h-5 w-5" />}
        breadcrumbs={[
          { label: "Configurações", href: "/dashboard/settings" },
          { label: "Integrações" },
          { label: "Tara-Balança" },
        ]}
      />
      <TaraConsole section="config" />
    </div>
  );
}
