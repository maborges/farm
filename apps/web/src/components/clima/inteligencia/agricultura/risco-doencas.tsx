"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Bug, ThermometerSun, Droplet, Filter, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { DropdownMenu, DropdownMenuItem, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

import { RiscoDoenca } from "@/lib/agricola/clima-api";

interface Props {
  /** Lista de riscos calculados pelo motor de inteligência do backend. */
  data?: RiscoDoenca[];
}

export function RiscoDoencasCard({ data }: Props) {
  const [selectedCulturas, setSelectedCulturas] = useState<string[]>([]);
  const riscos: RiscoDoenca[] = data ?? [];


  const getNivelColor = (nivel: string) => {
    switch (nivel) {
      case "baixo": return "bg-emerald-500";
      case "medio": return "bg-amber-400";
      case "alto": return "bg-orange-500";
      case "critico": return "bg-red-600";
      default: return "bg-slate-300";
    }
  };

  const getLabelColor = (nivel: string) => {
    switch (nivel) {
      case "baixo": return "text-emerald-700 bg-emerald-50 border-emerald-200";
      case "medio": return "text-amber-700 bg-amber-50 border-amber-200";
      case "alto": return "text-orange-700 bg-orange-50 border-orange-200";
      case "critico": return "text-red-700 bg-red-50 border-red-200";
      default: return "text-slate-700 bg-slate-50 border-slate-200";
    }
  };

  return (
    <Card className="rounded-sm flex flex-col h-full border-border/60">
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex flex-col gap-1.5">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bug className="h-5 w-5 text-purple-500" />
            Previsão de Risco de Doenças (Fitossanitário)
          </CardTitle>
          <CardDescription>
            Modelos climáticos de favorabilidade para surtos de fungos e bactérias.
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
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {riscos.filter(r => selectedCulturas.length === 0 || selectedCulturas.includes(r.cultura)).map((risco, index) => (
            <div key={index} className="p-4 rounded-sm border border-border bg-card flex flex-col gap-3">
              
              <div className="flex items-start justify-between">
                <div className="flex flex-col">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">{risco.cultura}</span>
                  <span className="font-bold">{risco.doenca}</span>
                </div>
                <div className={cn("px-2 py-1 rounded-sm text-[10px] font-bold uppercase border", getLabelColor(risco.nivel))}>
                  {risco.nivel}
                </div>
              </div>

              <div className="flex flex-col gap-1 mt-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Probabilidade</span>
                  <span className="font-bold">{risco.probabilidade_pct}%</span>
                </div>
                <Progress 
                  value={risco.probabilidade_pct} 
                  className="h-2"
                  indicatorClassName={getNivelColor(risco.nivel)}
                />
              </div>

              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground border-t border-border pt-3">
                <div className="flex items-center gap-1" title="Favorabilidade por Temperatura">
                  <ThermometerSun size={14} className={risco.probabilidade_pct > 50 ? "text-orange-500" : ""} />
                  <span>Temp. Ideal</span>
                </div>
                <div className="flex items-center gap-1" title="Favorabilidade por Umidade/Molhamento Foliar">
                  <Droplet size={14} className={risco.probabilidade_pct > 70 ? "text-blue-500" : ""} />
                  <span>Alta Umidade</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
