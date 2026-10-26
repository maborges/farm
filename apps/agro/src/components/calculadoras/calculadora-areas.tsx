"use client";

import React, { useState, useMemo } from "react";
import { Map, RotateCcw, AlertCircle, Info, ShieldAlert, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  converterAreaRural,
  type UnidadeAreaRural,
  type ConversaoAreaResultado,
} from "@/lib/calculadoras/core";
import { parseNumeroPtBr, formatarNumero, detectarEntradaAmbiguaPtBr } from "@/lib/calculadoras/format";

export function CalculadoraAreas() {
  const [valorTexto, setValorTexto] = useState<string>("10");
  const [unidade, setUnidade] = useState<UnidadeAreaRural>("HECTARES");

  const avisoAmbiguo = useMemo(() => {
    return detectarEntradaAmbiguaPtBr(valorTexto);
  }, [valorTexto]);

  const { resultado, erro } = useMemo<{
    resultado: ConversaoAreaResultado | null;
    erro: string | null;
  }>(() => {
    const valor = parseNumeroPtBr(valorTexto);

    if (valor === null) {
      return { resultado: null, erro: null };
    }

    try {
      const res = converterAreaRural({
        valor,
        unidadeOrigem: unidade,
      });
      return { resultado: res, erro: null };
    } catch (err) {
      return {
        resultado: null,
        erro: err instanceof Error ? err.message : "Erro no cálculo de área",
      };
    }
  }, [valorTexto, unidade]);

  const handleLimpar = () => {
    setValorTexto("");
    setUnidade("HECTARES");
  };

  return (
    <Card className="border border-border/80 shadow-xs">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
              <Map className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold">
                Conversão de Áreas Rurais
              </CardTitle>
              <CardDescription className="text-xs">
                Conversão exata entre Hectares, Metros Quadrados e os principais Alqueires regionais do Brasil.
              </CardDescription>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] hidden sm:inline-flex">
            Offline
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Aviso de Variação Regional do Alqueire com Fundamentação Geométrica */}
        <div className="p-2.5 rounded-sm border border-amber-500/30 bg-amber-500/5 text-xs text-foreground flex items-start gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-[11px] text-muted-foreground leading-relaxed space-y-1">
            <p>
              <span className="font-semibold text-foreground">Fundamentação dos Alqueires:</span> No Brasil colonial, a medida agrária base era a <em>braça linear</em> (2,20 m), correspondendo a braça quadrada de 4,84 m². O Alqueire Paulista adota 5.000 braças² (24.200 m²), o Alqueire Mineiro adota 10.000 braças² (48.400 m²), o Alqueire do Norte adota o padrão de 75×75 braças (5.625 braças² = 27.225 m²) e o Alqueire Baiano adota 50×50 braças (2.500 braças² = 12.100 m²).
            </p>
            <p className="text-[10px] text-amber-800 dark:text-amber-400">
              Sempre verifique a especificação exata da escritura do imóvel antes de transações comerciais.
            </p>
          </div>
        </div>

        {/* Formulário de Entradas */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="valor-area">Área a Converter</Label>
            <Input
              id="valor-area"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 50 ou 120,5"
              value={valorTexto}
              onChange={(e) => setValorTexto(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="unidade-area">Unidade de Origem</Label>
            <select
              id="unidade-area"
              value={unidade}
              onChange={(e) => setUnidade(e.target.value as UnidadeAreaRural)}
              className="flex h-8 w-full rounded-sm border border-border bg-background px-2.5 py-1 text-xs text-foreground shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="HECTARES">Hectares (ha) — 10.000 m²</option>
              <option value="METROS_QUADRADOS">Metros Quadrados (m²)</option>
              <option value="ALQUEIRE_PAULISTA">Alqueire Paulista — 24.200 m² (2,42 ha)</option>
              <option value="ALQUEIRE_MINEIRO">Alqueire Mineiro / Goiano — 48.400 m² (4,84 ha)</option>
              <option value="ALQUEIRE_NORTE">Alqueire do Norte (75×75 braças) — 27.225 m² (2,7225 ha)</option>
              <option value="ALQUEIRE_BAIANO">Alqueire Baiano / Pequeno (50×50 braças) — 12.100 m² (1,21 ha)</option>
            </select>
          </div>
        </div>

        {/* Aviso de Ambiguidade Numérica */}
        {avisoAmbiguo && (
          <div className="p-2.5 rounded-sm border border-amber-500/30 bg-amber-500/5 text-amber-900 dark:text-amber-300 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <span className="leading-relaxed">{avisoAmbiguo}</span>
          </div>
        )}

        {/* Mensagem de Erro de Validação */}
        {erro && (
          <div className="p-2.5 rounded-sm border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{erro}</span>
          </div>
        )}

        {/* Painel de Resultados */}
        {resultado && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Equivalências Calculadas
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-muted-foreground">Hectares (ha)</span>
                  <Badge variant="outline" className="text-[9px]">Padrão Oficial (SI)</Badge>
                </div>
                <span className="text-base sm:text-lg font-bold text-emerald-700 dark:text-emerald-400 block mt-1">
                  {formatarNumero(resultado.hectares, 4)} ha
                </span>
                <span className="text-[10px] text-muted-foreground">1 ha = 10.000 m²</span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Metros Quadrados (m²)</span>
                <span className="text-base sm:text-lg font-bold text-foreground block mt-1">
                  {formatarNumero(resultado.metrosQuadrados, 2)} m²
                </span>
                <span className="text-[10px] text-muted-foreground">Área geométrica total</span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Alqueire Paulista</span>
                <span className="text-base sm:text-lg font-bold text-foreground block mt-1">
                  {formatarNumero(resultado.alqueiresPaulistas, 4)} alq
                </span>
                <span className="text-[10px] text-muted-foreground">Fator: 24.200 m² (5.000 braças² = 2,42 ha)</span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Alqueire Mineiro / Goiano</span>
                <span className="text-base sm:text-lg font-bold text-foreground block mt-1">
                  {formatarNumero(resultado.alqueiresMineiros, 4)} alq
                </span>
                <span className="text-[10px] text-muted-foreground">Fator: 48.400 m² (100×100 braças = 4,84 ha)</span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Alqueire do Norte</span>
                <span className="text-base sm:text-lg font-bold text-foreground block mt-1">
                  {formatarNumero(resultado.alqueiresNorte, 4)} alq
                </span>
                <span className="text-[10px] text-muted-foreground">Fator: 27.225 m² (75×75 braças = 2,7225 ha)</span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Alqueire Baiano / Pequeno</span>
                <span className="text-base sm:text-lg font-bold text-foreground block mt-1">
                  {formatarNumero(resultado.alqueiresBaianos, 4)} alq
                </span>
                <span className="text-[10px] text-muted-foreground">Fator: 12.100 m² (50×50 braças = 1,21 ha - BA/MA/PI)</span>
              </div>
            </div>
          </div>
        )}

        {/* Memória e Ações */}
        <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-t border-border/60">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <span>Fatores verificados nas tabelas de medidas agrárias tradicionais do INCRA/IBGE.</span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleLimpar}
            className="flex items-center gap-1.5 self-end sm:self-auto cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Limpar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
