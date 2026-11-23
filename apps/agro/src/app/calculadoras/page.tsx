import type { Metadata } from "next";
import { Calculator } from "lucide-react";
import { CalculadorasContainer } from "@/components/calculadoras/calculadoras-container";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export const metadata: Metadata = {
  title: "Calculadoras e Conversores Agrícolas | DeepFarms Agro",
  description:
    "Ferramentas gratuitas de conversão de sacas, áreas rurais, alqueires, frete e custos por hectare. Funcionamento 100% offline.",
};

export default function CalculadorasPage() {
  return (
    <div className="flex flex-col gap-4">
      {/* Cabeçalho da Seção (no mobile a App Bar do Header já exibe título e subtítulo) */}
      <div className="hidden md:flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2 min-w-0">
            <Calculator className="size-5 text-emerald-700 dark:text-emerald-400 shrink-0" />
            <span>Calculadoras e Conversores Agrícolas</span>
          </h1>
          <Badge variant="recommendation" className="shrink-0">
            5 Ferramentas Prontas
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Cálculos operacionais da fazenda sem depender de sinal de internet ou planos pagos.
        </p>
      </div>

      <Separator className="hidden md:block" />

      {/* Conteúdo Interativo das Calculadoras */}
      <CalculadorasContainer />
    </div>
  );
}
