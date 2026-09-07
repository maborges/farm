import { BrainCircuit } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { InteligenciaPecuariaClient } from "./inteligencia-pecuaria-client";

export default function PecuariaClimaInteligenciaPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Painel Zoossanitário"
        description="Monitoramento avançado de bem-estar animal, risco térmico (ITH) e estresse climático."
        icon={<BrainCircuit className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Clima", href: "/dashboard/pecuaria/clima/monitoramento" }, { label: "Bem-Estar Animal" }]}
      />
      <InteligenciaPecuariaClient />
    </div>
  );
}
