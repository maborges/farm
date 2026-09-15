import { Smartphone } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { TaraConsole } from "@/components/balanca/tara-console";

export default function BalancaEstacoesPage() {
  return <div className="flex flex-col gap-6 p-6"><PageHeader title="Estações da Balança" description="Solicite a ativação de estações pela API pública da TARA." icon={<Smartphone className="h-5 w-5" />} breadcrumbs={[{ label: "Operacional" }, { label: "Balança", href: "/dashboard/operacional/balanca" }, { label: "Estações" }]} /><TaraConsole section="stations" /></div>;
}
