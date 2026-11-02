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
    <div className="max-w-3xl mx-auto flex flex-col gap-4 sm:gap-6">
      {/* Cabeçalho da Página */}
      <div className="flex flex-col gap-1 border-b border-border pb-3">
        <div className="flex items-center gap-2 text-primary">
          <Shield className="w-4 h-4 text-primary" />
          <span className="text-[11px] font-semibold uppercase tracking-wider">
            Identidade Individual Segregada
          </span>
        </div>
        <h1 className="text-base sm:text-xl md:text-2xl font-bold tracking-tight text-foreground">
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
