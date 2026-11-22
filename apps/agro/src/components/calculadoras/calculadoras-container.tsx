"use client";

import React, { useState } from "react";
import { ArrowRightLeft, DollarSign, Map, Scale, ShieldCheck, Truck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { HorizontalScrollRail } from "@/components/layout/horizontal-scroll-rail";
import { CalculadoraAreas } from "./calculadora-areas";
import { CalculadoraConversorGeral } from "./calculadora-conversor-geral";
import { CalculadoraCustoHectare } from "./calculadora-custo-hectare";
import { CalculadoraFrete } from "./calculadora-frete";
import { CalculadoraSacas } from "./calculadora-sacas";

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
    <div className="flex flex-col gap-3.5 sm:gap-4">
      {/* Barra de Navegação entre Ferramentas (Deslizante com Indicação no Mobile / Segmented no Tablet & Desktop) */}
      <HorizontalScrollRail
        role="tablist"
        ariaLabel="Selecionar calculadora agrícola"
        testId="calculadoras-segmented-bar"
        contentClassName="p-1 rounded-sm bg-muted/60 border border-border/60 sm:flex-wrap"
      >
        {ABAS_CALCULADORAS.map((aba) => {
          const Icone = aba.icone;
          const selecionada = ativa === aba.id;

          return (
            <Button
              key={aba.id}
              type="button"
              variant={selecionada ? "default" : "ghost"}
              size="sm"
              onClick={() => setAtiva(aba.id)}
              aria-pressed={selecionada}
              className="shrink-0 snap-start min-h-[34px] sm:min-h-[30px]"
            >
              <Icone className="size-3.5" />
              <span className="hidden sm:inline">{aba.nome}</span>
              <span className="sm:hidden">{aba.rotuloCurto}</span>
            </Button>
          );
        })}
      </HorizontalScrollRail>

      {/* Conteúdo da Calculadora Ativa */}
      <div>
        {ativa === "sacas" && <CalculadoraSacas />}
        {ativa === "areas" && <CalculadoraAreas />}
        {ativa === "frete" && <CalculadoraFrete />}
        {ativa === "custo-hectare" && <CalculadoraCustoHectare />}
        {ativa === "unidades" && <CalculadoraConversorGeral />}
      </div>

      {/* Selo de Segurança e Funcionamento 100% Offline */}
      <Alert variant="success">
        <ShieldCheck className="size-4" />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <AlertTitle className="text-xs">Calculadoras 100% Autônomas</AlertTitle>
            <AlertDescription className="text-xs">
              Nenhum dado é transmitido para a nuvem. Todas as conversões e contas são executadas diretamente no seu aparelho.
            </AlertDescription>
          </div>
          <Badge variant="recommendation" className="shrink-0 hidden md:inline-flex">
            Privacidade &amp; Zero Dados Coletados
          </Badge>
        </div>
      </Alert>
    </div>
  );
}
