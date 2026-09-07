import { Scale } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { TaraConsole } from "@/components/balanca/tara-console";

export default function BalancaPage() {
  return <div className="flex flex-col gap-6 p-6"><PageHeader title="Balança" description="Integração operacional com a Plataforma TARA." icon={<Scale className="h-5 w-5" />} breadcrumbs={[{ label: "Operacional" }, { label: "Balança" }]} /><TaraConsole /></div>;
}
