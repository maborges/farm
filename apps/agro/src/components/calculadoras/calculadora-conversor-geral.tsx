"use client";

import React, { useState, useMemo } from "react";
import { ArrowRightLeft, RotateCcw, AlertCircle, Info, ArrowLeftRight, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  converterUnidadeGeral,
  type CategoriaGrandeza,
  CATALOGO_UNIDADES,
} from "@/lib/calculadoras/core";
import { parseNumeroPtBr, formatarNumero, detectarEntradaAmbiguaPtBr } from "@/lib/calculadoras/format";

const UNIDADES_POR_CATEGORIA: Record<CategoriaGrandeza, string[]> = {
  MASSA: ["KG", "G", "TONELADA", "ARROBA"],
  AREA: ["M2", "HECTARE", "KM2"],
  VOLUME: ["LITRO", "MILILITRO", "METRO_CUBICO"],
  COMPRIMENTO: ["METRO", "QUILOMETRO", "CENTIMETRO"],
};

export function CalculadoraConversorGeral() {
  const [categoria, setCategoria] = useState<CategoriaGrandeza>("MASSA");
  const [unidadeDe, setUnidadeDe] = useState<string>("KG");
  const [unidadePara, setUnidadePara] = useState<string>("TONELADA");
  const [valorTexto, setValorTexto] = useState<string>("1000");

  const avisoAmbiguo = useMemo(() => {
    return detectarEntradaAmbiguaPtBr(valorTexto);
  }, [valorTexto]);

  const handleTrocarCategoria = (novaCategoria: CategoriaGrandeza) => {
    setCategoria(novaCategoria);
    const lista = UNIDADES_POR_CATEGORIA[novaCategoria];
    setUnidadeDe(lista[0]);
    setUnidadePara(lista[1] ?? lista[0]);
  };

  const handleInverter = () => {
    const temp = unidadeDe;
    setUnidadeDe(unidadePara);
    setUnidadePara(temp);
  };

  const handleLimpar = () => {
    setValorTexto("");
  };

  const { resultado, erro } = useMemo<{
    resultado: number | null;
    erro: string | null;
  }>(() => {
    const valor = parseNumeroPtBr(valorTexto);

    if (valor === null) {
      return { resultado: null, erro: null };
    }

    try {
      const res = converterUnidadeGeral(valor, unidadeDe, unidadePara);
      return { resultado: res, erro: null };
    } catch (err) {
      return {
        resultado: null,
        erro: err instanceof Error ? err.message : "Erro na conversão",
      };
    }
  }, [valorTexto, unidadeDe, unidadePara]);

  const defDe = CATALOGO_UNIDADES[unidadeDe];
  const defPara = CATALOGO_UNIDADES[unidadePara];

  return (
    <Card className="border border-border/80 shadow-xs">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
              <ArrowRightLeft className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold">
                Conversor Geral de Unidades
              </CardTitle>
              <CardDescription className="text-xs">
                Conversão de grandezas compatíveis: Massa, Área, Volume e Comprimento com proteção dimensional.
              </CardDescription>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] hidden sm:inline-flex">
            Offline
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Seletor de Categoria de Grandeza */}
        <div className="space-y-1.5">
          <Label>Selecione a Grandeza Física</Label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {(["MASSA", "AREA", "VOLUME", "COMPRIMENTO"] as CategoriaGrandeza[]).map((cat) => {
              const ativo = categoria === cat;
              const rotulos: Record<CategoriaGrandeza, string> = {
                MASSA: "Massa (kg, t, @)",
                AREA: "Área (m², ha, km²)",
                VOLUME: "Volume (L, mL, m³)",
                COMPRIMENTO: "Comprimento (m, km)",
              };

              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => handleTrocarCategoria(cat)}
                  className={`px-3 py-2 text-xs font-medium rounded-sm border transition-all text-left cursor-pointer ${
                    ativo
                      ? "border-emerald-600 bg-emerald-600/10 text-emerald-800 dark:text-emerald-400 font-semibold"
                      : "border-border bg-background hover:bg-muted text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {rotulos[cat]}
                </button>
              );
            })}
          </div>
        </div>

        {/* Formulário de Entradas e Seleção de Unidades */}
        <div className="grid grid-cols-1 sm:grid-cols-7 gap-2.5 items-end">
          <div className="space-y-1.5 sm:col-span-3">
            <Label htmlFor="valor-conversao">Valor</Label>
            <Input
              id="valor-conversao"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 1000"
              value={valorTexto}
              onChange={(e) => setValorTexto(e.target.value)}
            />
            <select
              id="unidade-de"
              value={unidadeDe}
              onChange={(e) => setUnidadeDe(e.target.value)}
              className="mt-1 flex h-8 w-full rounded-sm border border-border bg-background px-2.5 py-1 text-xs text-foreground shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {UNIDADES_POR_CATEGORIA[categoria].map((codigo) => {
                const u = CATALOGO_UNIDADES[codigo];
                return (
                  <option key={codigo} value={codigo}>
                    {u.nome} ({u.simbolo})
                  </option>
                );
              })}
            </select>
          </div>

          <div className="sm:col-span-1 flex justify-center pb-1">
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleInverter}
              className="h-8 w-8 rounded-sm cursor-pointer"
              title="Inverter unidades"
            >
              <ArrowLeftRight className="w-3.5 h-3.5" />
            </Button>
          </div>

          <div className="space-y-1.5 sm:col-span-3">
            <Label htmlFor="unidade-para">Para</Label>
            <div className="h-8 flex items-center px-2.5 text-xs text-muted-foreground bg-muted/40 rounded-sm border border-border/60">
              {resultado !== null ? (
                <span className="font-semibold text-foreground truncate">
                  {formatarNumero(resultado, 6)} {defPara?.simbolo}
                </span>
              ) : (
                "Aguardando valor..."
              )}
            </div>
            <select
              id="unidade-para"
              value={unidadePara}
              onChange={(e) => setUnidadePara(e.target.value)}
              className="mt-1 flex h-8 w-full rounded-sm border border-border bg-background px-2.5 py-1 text-xs text-foreground shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {UNIDADES_POR_CATEGORIA[categoria].map((codigo) => {
                const u = CATALOGO_UNIDADES[codigo];
                return (
                  <option key={codigo} value={codigo}>
                    {u.nome} ({u.simbolo})
                  </option>
                );
              })}
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

        {/* Destaque do Resultado */}
        {resultado !== null && defDe && defPara && (
          <div className="p-4 rounded-sm bg-muted/40 border border-border/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <span className="text-[11px] text-muted-foreground block">Conversão Final</span>
              <div className="text-lg sm:text-xl font-bold text-emerald-700 dark:text-emerald-400">
                {valorTexto} {defDe.simbolo} = {formatarNumero(resultado, 6)} {defPara.simbolo}
              </div>
              <span className="text-[10px] text-muted-foreground">
                {defDe.nome} ({defDe.simbolo}) para {defPara.nome} ({defPara.simbolo})
              </span>
            </div>
          </div>
        )}

        {/* Memória de Cálculo e Ações */}
        <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-t border-border/60">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <span>Conversão estrita pelo Sistema Internacional (SI). Grandezas incompatíveis são bloqueadas.</span>
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
