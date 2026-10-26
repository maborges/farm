"use client";

import React, { useState } from "react";
import { Scale, Map, Truck, DollarSign, ArrowRightLeft, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { CalculadoraSacas } from "./calculadora-sacas";
import { CalculadoraAreas } from "./calculadora-areas";
import { CalculadoraFrete } from "./calculadora-frete";
import { CalculadoraCustoHectare } from "./calculadora-custo-hectare";
import { CalculadoraConversorGeral } from "./calculadora-conversor-geral";

export type IdCalculadora =
  | "sacas"
  | "areas"
  | "frete"
  | "custo-hectare"
  | "unidades";

interface AbaCalculadora {
  id: IdCalculadora;
  nome: string;
  rotuloCurto: string;
  icone: React.ComponentType<{ className?: string }>;
}

const ABAS_CALCULADORAS: AbaCalculadora[] = [
  {
    id: "sacas",
    nome: "Sacas, Kg e Toneladas",
    rotuloCurto: "Sacas / Kg / t",
    icone: Scale,
  },
  {
    id: "areas",
    nome: "Áreas Rurais (Alqueires / Hectares)",
    rotuloCurto: "Áreas Rurais",
    icone: Map,
  },
  {
    id: "frete",
    nome: "Estimativa de Frete",
    rotuloCurto: "Frete Agrícola",
    icone: Truck,
  },
  {
    id: "custo-hectare",
    nome: "Custo por Hectare e Break-Even",
    rotuloCurto: "Custo & Equilíbrio",
    icone: DollarSign,
  },
  {
    id: "unidades",
    nome: "Conversor Geral de Unidades",
    rotuloCurto: "Conversor Geral",
    icone: ArrowRightLeft,
  },
];

export function CalculadorasContainer() {
  const [ativa, setAtiva] = useState<IdCalculadora>("sacas");

  return (
    <div className="space-y-4">
      {/* Barra de Navegação entre Ferramentas */}
      <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-sm bg-muted/40 border border-border/60">
        {ABAS_CALCULADORAS.map((aba) => {
          const Icone = aba.icone;
          const selecionada = ativa === aba.id;

          return (
            <button
              key={aba.id}
              type="button"
              onClick={() => setAtiva(aba.id)}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-sm transition-all cursor-pointer ${
                selecionada
                  ? "bg-background text-foreground shadow-xs border border-border/80 font-semibold"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
              }`}
            >
              <Icone className={`w-3.5 h-3.5 ${selecionada ? "text-emerald-700 dark:text-emerald-400" : ""}`} />
              <span className="hidden sm:inline">{aba.nome}</span>
              <span className="sm:hidden">{aba.rotuloCurto}</span>
            </button>
          );
        })}
      </div>

      {/* Conteúdo da Calculadora Ativa */}
      <div>
        {ativa === "sacas" && <CalculadoraSacas />}
        {ativa === "areas" && <CalculadoraAreas />}
        {ativa === "frete" && <CalculadoraFrete />}
        {ativa === "custo-hectare" && <CalculadoraCustoHectare />}
        {ativa === "unidades" && <CalculadoraConversorGeral />}
      </div>

      {/* Selo de Segurança e Funcionamento 100% Offline */}
      <div className="p-3 rounded-sm border border-emerald-600/20 bg-emerald-600/5 flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
          <span>
            <strong>Calculadoras 100% Autônomas:</strong> Nenhum dado é transmitido para a nuvem. Todas as conversões e contas são executadas diretamente no seu aparelho.
          </span>
        </div>
        <Badge variant="outline" className="text-[10px] border-emerald-600/30 text-emerald-700 dark:text-emerald-400 shrink-0 hidden md:inline-flex">
          Privacidade & Zero Dados Coletados
        </Badge>
      </div>
    </div>
  );
}
