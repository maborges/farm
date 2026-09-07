import { PageHeader } from "@/components/shared/page-header";
import { BrainCircuit } from "lucide-react";
import { IASettingsClient } from "./ia-settings-client";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Configurações de IA | AgroSaaS",
  description: "Gerencie o Autopilot, Personas e Experimentos de IA.",
};

export default function IAAutopilotSettingsPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Inteligência Artificial"
        description="Gestão de autonomia, perfis comportamentais e experimentos de growth."
        icon={<BrainCircuit className="h-8 w-8 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Configurações", href: "/dashboard/settings/account" },
          { label: "Inteligência Artificial" }
        ]}
      />

      <IASettingsClient />
    </div>
  );
}
