import type { Metadata } from "next";
import { Shield } from "lucide-react";
import { PainelConta } from "@/components/auth/painel-conta";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export const metadata: Metadata = {
  title: "Conta Individual Segregada | DeepFarms Agro",
  description:
    "Gerencie sua conta individual no DeepFarms Agro de forma segura e segregada do SaaS comercial, sem criação de empresas artificiais.",
};

export default function ContaPage() {
  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-4 sm:gap-5">
      {/* Cabeçalho da Página */}
      <div className="flex flex-col gap-1">
        <div className="hidden md:flex items-center gap-2">
          <Badge variant="default" className="gap-1">
            <Shield className="size-3" />
            <span>Identidade Individual Segregada</span>
          </Badge>
        </div>
        <h1 className="text-base sm:text-xl md:text-2xl font-bold tracking-tight text-foreground">
          Minha Conta DeepFarms Agro
        </h1>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Acesso opcional e individual para o produtor rural. O aplicativo continua 100% público, gratuito e anônimo para consultas e ferramentas.
        </p>
      </div>

      <Separator className="hidden md:block" />

      {/* Painel Interativo de Conta */}
      <PainelConta />
    </div>
  );
}
