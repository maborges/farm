import { Users } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { TaraConsole } from "@/components/balanca/tara-console";

export default function BalancaOperadoresPage() {
  return <div className="flex flex-col gap-6 p-6"><PageHeader title="Operadores da Balança" description="Sincronize a projeção técnica dos operadores com o Pondaxis." icon={<Users className="h-5 w-5" />} breadcrumbs={[{ label: "Operacional" }, { label: "Balança", href: "/dashboard/operacional/balanca" }, { label: "Operadores" }]} /><TaraConsole section="operators" /></div>;
}
