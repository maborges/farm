"use client";

import React, { useState, useMemo } from "react";
import { ArrowRightLeft, RotateCcw, AlertCircle, Info, ArrowLeftRight, AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, inputBaseClassName } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  converterUnidadeGeral,
  type CategoriaGrandeza,
  CATALOGO_UNIDADES,
} from "@/lib/calculadoras/core";
import { parseNumeroPtBr, formatarNumero, detectarEntradaAmbiguaPtBr } from "@/lib/calculadoras/format";
import { cn } from "@/lib/utils";

const UNIDADES_POR_CATEGORIA: Record<CategoriaGrandeza, string[]> = {
  MASSA: ["KG", "G", "TONELADA", "ARROBA"],
  AREA: ["M2", "HECTARE", "KM2"],
  VOLUME: ["LITRO", "MILILITRO", "METRO_CUBICO"],
  COMPRIMENTO: ["METRO", "QUILOMETRO", "CENTIMETRO"],
};

const ROTULOS_CATEGORIA: Record<CategoriaGrandeza, string> = {
  MASSA: "Massa (kg, t, @)",
  AREA: "Área (m², ha, km²)",
  VOLUME: "Volume (L, mL, m³)",
  COMPRIMENTO: "Comprimento (m, km)",
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
    <Card>
      <CardHeader className="border-b border-border/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
            <ArrowRightLeft className="size-5" />
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
        <CardAction>
          <Badge variant="outline" className="hidden sm:inline-flex">
            Offline
          </Badge>
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Seletor de Categoria de Grandeza via ToggleGroup */}
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs">Selecione a Grandeza Física</Label>
          <ToggleGroup
            type="single"
            value={categoria}
            onValueChange={(val) => {
              if (typeof val === "string" && val) {
                handleTrocarCategoria(val as CategoriaGrandeza);
              }
            }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-2"
          >
            {(["MASSA", "AREA", "VOLUME", "COMPRIMENTO"] as CategoriaGrandeza[]).map((cat) => (
              <ToggleGroupItem
                key={cat}
                value={cat}
                className="justify-start text-xs h-8"
              >
                {ROTULOS_CATEGORIA[cat]}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>

        {/* Formulário de Entradas e Seleção de Unidades */}
        <div className="grid grid-cols-1 sm:grid-cols-7 gap-2.5 items-end">
          <div className="flex flex-col gap-1.5 sm:col-span-3">
            <Label htmlFor="valor-conversao" className="text-xs">Valor</Label>
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
              className={cn(inputBaseClassName, "text-xs")}
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
              title="Inverter unidades"
            >
              <ArrowLeftRight className="size-3.5" />
            </Button>
          </div>

          <div className="flex flex-col gap-1.5 sm:col-span-3">
            <Label htmlFor="unidade-para" className="text-xs">Para</Label>
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
              className={cn(inputBaseClassName, "text-xs")}
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
          <Alert variant="warning">
            <AlertTriangle className="size-4" />
            <AlertDescription className="text-xs">{avisoAmbiguo}</AlertDescription>
          </Alert>
        )}

        {/* Mensagem de Erro de Validação */}
        {erro && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertDescription className="text-xs">{erro}</AlertDescription>
          </Alert>
        )}

        {/* Destaque do Resultado */}
        {resultado !== null && defDe && defPara && (
          <Card variant="muted" size="sm">
            <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <span className="text-[11px] text-muted-foreground block">Conversão Final</span>
                <div className="text-lg sm:text-xl font-bold text-emerald-700 dark:text-emerald-400">
                  {valorTexto} {defDe.simbolo} = {formatarNumero(resultado, 6)} {defPara.simbolo}
                </div>
                <span className="text-[10px] text-muted-foreground">
                  {defDe.nome} ({defDe.simbolo}) para {defPara.nome} ({defPara.simbolo})
                </span>
              </div>
            </CardContent>
          </Card>
        )}

        <Separator />

        {/* Memória de Cálculo e Ações */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="size-3.5 text-muted-foreground shrink-0" />
            <span>Conversão estrita pelo Sistema Internacional (SI). Grandezas incompatíveis são bloqueadas.</span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleLimpar}
            className="self-end sm:self-auto"
          >
            <RotateCcw className="size-3.5" />
            <span>Limpar</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
