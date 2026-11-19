"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Bug, Filter, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { DropdownMenu, DropdownMenuItem, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

import { RiscoDoenca, RiscoFitossanitarioStatus } from "@/lib/agricola/clima-api";

interface Props {
  /** Pontuações de favorabilidade climática calculadas pelo backend. */
  data?: RiscoDoenca[];
  status?: RiscoFitossanitarioStatus;
}

export function RiscoDoencasCard({ data, status }: Props) {
  const [selectedCulturas, setSelectedCulturas] = useState<string[]>([]);
  const riscos: RiscoDoenca[] = data ?? [];


  const getNivelColor = (nivel: string) => {
    switch (nivel) {
      case "baixa": return "bg-emerald-500";
      case "moderada": return "bg-amber-400";
      case "alta": return "bg-orange-500";
      case "muito_alta": return "bg-red-600";
      default: return "bg-slate-300";
    }
  };

  const getLabelColor = (nivel: string) => {
    switch (nivel) {
      case "baixa": return "text-emerald-700 bg-emerald-50 border-emerald-200";
      case "moderada": return "text-amber-700 bg-amber-50 border-amber-200";
      case "alta": return "text-orange-700 bg-orange-50 border-orange-200";
      case "muito_alta": return "text-red-700 bg-red-50 border-red-200";
      default: return "text-slate-700 bg-slate-50 border-slate-200";
    }
  };

  const statusText: Record<RiscoFitossanitarioStatus, string> = {
    SEM_CULTURA_ATIVA: "Nenhuma cultura ativa foi encontrada para esta unidade.",
    SEM_MODELO_APLICAVEL: "Não há modelo personalizado cadastrado para as culturas ativas. Cadastre um modelo próprio ou copie um modelo-base do sistema em Modelos Fitossanitários.",
    DADOS_CLIMATICOS_INSUFICIENTES: "Histórico climático insuficiente para avaliar os modelos disponíveis.",
    DADOS_CLIMATICOS_INVALIDOS: "Há medições climáticas inválidas para as variáveis exigidas pelos modelos.",
    CONFIGURACAO_INVALIDA: "Um ou mais modelos possuem regras inválidas e não foram avaliados.",
    PARCIAL: "Resultado parcial: alguns modelos não puderam ser avaliados com os dados disponíveis.",
    CALCULADO: "Pontuação heurística de favorabilidade climática. Não confirma doença nem indica aplicação de defensivos.",
  };

  return (
    <Card className="rounded-sm flex flex-col h-full border-border/60">
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex flex-col gap-1.5">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bug className="h-5 w-5 text-purple-500" />
            Favorabilidade Climática Fitossanitária
          </CardTitle>
          <CardDescription>
            Favorabilidade das condições climáticas observadas; não é diagnóstico nem probabilidade de doença.
          </CardDescription>
        </div>
        <div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 text-xs flex items-center gap-2">
                <Filter size={14} />
                Filtrar Culturas
                {selectedCulturas.length > 0 && (
                  <span className="bg-primary text-primary-foreground text-[10px] rounded-full px-2 py-0.5 ml-1">
                    {selectedCulturas.length}
                  </span>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel className="text-xs">Culturas Identificadas</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {Array.from(new Set(riscos.map((r) => r.cultura))).map((cultura) => (
                <DropdownMenuItem
                  key={cultura}
                  className="text-xs flex items-center gap-2 cursor-pointer"
                  onClick={(e) => {
                    e.preventDefault(); // Evita fechar o menu ao clicar
                    setSelectedCulturas((prev) =>
                      prev.includes(cultura) ? prev.filter((c) => c !== cultura) : [...prev, cultura]
                    );
                  }}
                >
                  <div className="w-4 h-4 flex items-center justify-center border rounded-sm border-primary">
                    {selectedCulturas.includes(cultura) && <Check size={12} />}
                  </div>
                  {cultura}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        {status && (
          <p className="mb-4 rounded-sm bg-muted/50 p-3 text-sm text-muted-foreground" role="status">
            {statusText[status]}
          </p>
        )}
        {riscos.length === 0 && (
          <p className="py-5 text-center text-sm text-muted-foreground">
            Nenhuma pontuação de favorabilidade foi calculada. Ausência de resultado não significa risco baixo.
          </p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {riscos.filter(r => selectedCulturas.length === 0 || selectedCulturas.includes(r.cultura)).map((risco, index) => (
            <div key={index} className="p-4 rounded-sm border border-border bg-card flex flex-col gap-3">
              
              <div className="flex items-start justify-between">
                <div className="flex flex-col">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">{risco.cultura}</span>
                  <span className="font-bold">{risco.doenca}</span>
                </div>
                <div className={cn("px-2 py-1 rounded-sm text-[10px] font-bold uppercase border", getLabelColor(risco.nivel_favorabilidade))}>
                  {risco.nivel_favorabilidade.replace("_", " ")}
                </div>
              </div>

              <div className="flex flex-col gap-1 mt-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Favorabilidade climática</span>
                  <span className="font-bold">{risco.favorabilidade_pct}%</span>
                </div>
                <Progress 
                  value={risco.favorabilidade_pct}
                  className="h-2"
                  indicatorClassName={getNivelColor(risco.nivel_favorabilidade)}
                />
              </div>
              <p className="mt-2 border-t border-border pt-3 text-xs text-muted-foreground">
                Indicador climático heurístico. Confirme sintomas e condições da lavoura em campo.
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
