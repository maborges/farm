import type { Metadata } from "next";
import { Shield } from "lucide-react";
import { PainelConta } from "@/components/auth/painel-conta";

export const metadata: Metadata = {
  title: "Conta Individual Segregada | DeepFarms Agro",
  description:
    "Gerencie sua conta individual no DeepFarms Agro de forma segura e segregada do SaaS comercial, sem criação de empresas artificiais.",
};

export default function ContaPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-12 space-y-6">
      {/* Cabeçalho da Página */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 text-primary">
          <Shield className="w-5 h-5 text-primary" />
          <span className="text-xs font-semibold uppercase tracking-wider">
            Identidade Individual Segregada
          </span>
        </div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          Minha Conta DeepFarms Agro
        </h1>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Acesso opcional e individual para o produtor rural. O aplicativo continua 100% público, gratuito e anônimo para consultas e ferramentas.
        </p>
      </div>

      {/* Painel Interativo de Conta */}
      <PainelConta />
    </div>
  );
}
