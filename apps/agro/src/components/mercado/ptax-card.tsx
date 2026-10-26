"use client";

import { useEffect, useState } from "react";
import { Building2, Clock3, DollarSign, Info, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CURRENCIES, fetchPtaxIntraday, formatCurrencyRate, formatDateBr,
  formatSyncBr, formatTimeBr,
  type EstadoDisponibilidadePtax, type PtaxIntradayPoint,
} from "@/lib/mercado/ptax";
import { useMoedaMercado } from "@/lib/mercado/moeda-store";

const AVISO = "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. Não representa cotação de câmbio em tempo real.";

function statusLabel(state: EstadoDisponibilidadePtax): string {
  switch (state) {
    case "NORMAL": return "Último fechamento oficial disponível";
    case "FONTE_INDISPONIVEL": return "Último fechamento conhecido — fonte indisponível";
    case "OFFLINE": return "Modo offline — dado salvo";
    case "INDISPONIVEL": return "Cotação indisponível";
  }
}

function PtaxIntradayChart({ points }: { points: PtaxIntradayPoint[] }) {
  if (points.length < 2) return null;
  const values = points.flatMap((point) => [point.compra, point.venda]);
  const floor = Math.min(...values);
  const ceiling = Math.max(...values);
  const padding = Math.max((ceiling - floor) * 0.2, 0.0005);
  const low = floor - padding;
  const height = 96;
  const width = 336;
  const position = (value: number, index: number) => ({
    x: 12 + (index * (width - 24)) / (points.length - 1),
    y: 8 + ((ceiling + padding - value) * (height - 20)) / (ceiling + padding - low),
  });
  const line = (key: "compra" | "venda") => points.map((point, index) => {
    const { x, y } = position(point[key], index);
    return `${x},${y}`;
  }).join(" ");

  return (
    <section className="rounded-sm border border-border/60 bg-muted/20 p-3" aria-label="Oscilação intradiária da PTAX">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-foreground">Oscilação no dia</p>
        <p className="text-[10px] text-muted-foreground">Boletins PTAX oficiais</p>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-24 w-full" role="img" aria-label="Gráfico das cotações de compra e venda publicadas pelo BCB durante o dia">
        {[28, 56, 84].map((y) => <line key={y} x1="12" x2={width - 12} y1={y} y2={y} className="stroke-border" strokeDasharray="3 3" />)}
        <polyline fill="none" points={line("compra")} className="stroke-emerald-600" strokeWidth="2" />
        <polyline fill="none" points={line("venda")} className="stroke-sky-600" strokeWidth="2" />
        {points.map((point, index) => {
          const buy = position(point.compra, index);
          const sell = position(point.venda, index);
          return <g key={`${point.hora}-${point.tipoBoletim}`}>
            <circle cx={buy.x} cy={buy.y} r="2.5" className="fill-emerald-600" />
            <circle cx={sell.x} cy={sell.y} r="2.5" className="fill-sky-600" />
            <text x={buy.x} y="95" textAnchor="middle" className="fill-muted-foreground text-[8px]">{point.hora}</text>
          </g>;
        })}
      </svg>
      <div className="mt-1 flex gap-3 text-[10px] text-muted-foreground"><span><i className="mr-1 inline-block size-2 rounded-full bg-emerald-600" />Compra</span><span><i className="mr-1 inline-block size-2 rounded-full bg-sky-600" />Venda</span></div>
    </section>
  );
}

export function PtaxCard() {
  const { currency, quote, loading, state, setCurrency } = useMoedaMercado();
  const [intraday, setIntraday] = useState<PtaxIntradayPoint[]>([]);
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function loadIntraday() {
      if (!quote || quote.moeda !== currency || !quote.dataCotacao || !navigator.onLine) {
        setIntraday([]);
        return;
      }
      try {
        const points = await fetchPtaxIntraday(quote.dataCotacao, controller.signal, currency);
        if (active && !controller.signal.aborted) {
          setIntraday(points);
        }
      } catch {
        if (active) setIntraday([]);
      }
    }

    void loadIntraday();

    return () => {
      active = false;
      controller.abort();
    };
  }, [currency, quote]);

  const visibleQuote = quote?.moeda === currency ? quote : null;
  const effectiveState: EstadoDisponibilidadePtax = isOffline
    ? visibleQuote
      ? "OFFLINE"
      : "INDISPONIVEL"
    : state;
  const shownState = visibleQuote ? effectiveState : "INDISPONIVEL";
  return (
    <Card className="sm:col-span-2 lg:col-span-3" aria-label="Câmbio PTAX — Banco Central do Brasil">
      <CardHeader className="border-b border-border/60">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="rounded-sm bg-emerald-600/10 p-2 text-emerald-700 dark:text-emerald-400"><DollarSign className="h-5 w-5" /></div>
            <div>
              <CardTitle>Câmbio PTAX — Banco Central do Brasil</CardTitle>
              <p className="mt-1 text-[11px] text-muted-foreground">Taxa de referência oficial · valor em reais por unidade da moeda</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <label htmlFor="ptax-currency" className="sr-only">Moeda para consultar</label>
            <select
              id="ptax-currency"
              aria-label="Moeda para consultar"
              className="min-h-8 rounded-sm border border-border bg-background px-2 py-1 text-xs text-foreground"
              value={currency}
              onChange={(event) => {
                const selected = CURRENCIES.find((item) => item.code === event.target.value)?.code;
                if (selected) {
                  setCurrency(selected);
                }
              }}
            >
              <optgroup label="Moedas padrão">
                {CURRENCIES.slice(0, 2).map((item) => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}
              </optgroup>
              <optgroup label="Outras moedas">
                {CURRENCIES.slice(2).map((item) => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}
              </optgroup>
            </select>
            <Badge variant={shownState === "NORMAL" ? "success" : shownState === "INDISPONIVEL" ? "destructive" : "warning"}>{statusLabel(shownState)}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {visibleQuote ? (
          <div className="grid grid-cols-2 gap-3" aria-live="polite">
            <div className="rounded-sm border border-border/60 bg-muted/40 p-3">
              <p className="text-xs text-muted-foreground">Compra</p>
              <p className="mt-1 text-xl font-bold tabular-nums text-foreground">{formatCurrencyRate(visibleQuote.cotacaoCompra!, currency)}</p>
            </div>
            <div className="rounded-sm border border-border/60 bg-muted/40 p-3">
              <p className="text-xs text-muted-foreground">Venda</p>
              <p className="mt-1 text-xl font-bold tabular-nums text-foreground">{formatCurrencyRate(visibleQuote.cotacaoVenda!, currency)}</p>
            </div>
          </div>
        ) : (
          <div className="rounded-sm border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground" role="status">
            {loading ? "Consultando o último fechamento oficial…" : "Cotação indisponível. Tente novamente quando houver conexão."}
          </div>
        )}
        {loading && visibleQuote && (
          <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground" role="status">
            <RefreshCw className="size-3 animate-spin" /> Atualizando cotação de {currency}…
          </p>
        )}
        {visibleQuote && (
          <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <p><Clock3 className="mr-1 inline h-3.5 w-3.5" />{visibleQuote.tipoBoletim}: <strong className="text-foreground">{formatDateBr(visibleQuote.dataCotacao!)} às {formatTimeBr(visibleQuote.dataHoraBoletimIso!)} (São Paulo)</strong></p>
            <p><RefreshCw className="mr-1 inline h-3.5 w-3.5" />Última sincronização: <strong className="text-foreground">{formatSyncBr(visibleQuote.cacheAtualizadoEmIso!)} (São Paulo)</strong></p>
          </div>
        )}
        <PtaxIntradayChart points={visibleQuote ? intraday : []} />
        <p className="text-xs text-muted-foreground"><Building2 className="mr-1 inline h-3.5 w-3.5" />Fonte: Banco Central do Brasil (BCB)</p>
        <p className="flex gap-2 rounded-sm border border-sky-600/20 bg-sky-600/5 p-3 text-xs text-foreground"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-700 dark:text-sky-400" />{AVISO}</p>
      </CardContent>
    </Card>
  );
}
