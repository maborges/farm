import { Scale } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { TaraConsole } from "@/components/balanca/tara-console";

export default function BalancaPesagensPage() {
  return <div className="flex flex-col gap-6 p-6"><PageHeader title="Pesagens da Balança" description="Acompanhe a integração por API e Webhook com o Pondaxis." icon={<Scale className="h-5 w-5" />} breadcrumbs={[{ label: "Operacional" }, { label: "Balança", href: "/dashboard/operacional/balanca" }, { label: "Pesagens" }]} /><TaraConsole section="weighings" /></div>;
}
