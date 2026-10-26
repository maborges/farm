import type { Metadata } from "next";
import { Calculator } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { CalculadorasContainer } from "@/components/calculadoras/calculadoras-container";

export const metadata: Metadata = {
  title: "Calculadoras e Conversores Agrícolas | DeepFarms Agro",
  description:
    "Ferramentas gratuitas de conversão de sacas, áreas rurais, alqueires, frete e custos por hectare. Funcionamento 100% offline.",
};

export default function CalculadorasPage() {
  return (
    <div className="space-y-4">
      {/* Cabeçalho da Seção */}
      <div className="border-b border-border pb-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Calculator className="w-5 h-5 text-emerald-700 dark:text-emerald-400" />
              Calculadoras e Conversores Agrícolas
            </h1>
          </div>
          <Badge variant="outline" className="text-[10px] border-emerald-600/30 text-emerald-700 dark:text-emerald-400">
            5 Ferramentas Prontas
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Cálculos operacionais da fazenda sem depender de sinal de internet ou planos pagos.
        </p>
      </div>

      {/* Conteúdo Interativo das Calculadoras */}
      <CalculadorasContainer />
    </div>
  );
}
