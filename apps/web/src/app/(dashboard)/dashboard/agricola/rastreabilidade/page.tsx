"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    QrCode, Award, FileCheck, History, Plus, Download,
    ExternalLink, ShieldCheck, Calendar, MapPin,
    Sprout, Tractor, Wheat, Package, ChevronRight,
    FlaskConical, Layers, BarChart3, X, Printer,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
    Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "@/components/ui/sheet";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Lote {
    id: string;
    codigo_lote: string;
    produto: string;
    variedade?: string;
    quantidade_total: number;
    unidade: string;
    status: string;
    certificacoes: string[];
    data_geracao: string;
}

interface Cadeia {
    lote: {
        codigo_lote: string; produto: string; variedade?: string;
        quantidade_total: number; unidade: string; status: string;
        certificacoes: string[]; qr_code_url?: string; data_geracao: string;
    };
    safra: { cultura: string; ano_safra: number; area_plantada_ha: number; status: string };
    talhao: { nome: string; area_ha: number } | null;
    operacoes: Array<{
        id: string; tipo: string; subtipo?: string; descricao: string;
        data_realizada: string; area_aplicada_ha: number; custo_total: number; status: string;
        insumos: Array<{ produto_nome: string; unidade: string; dose_por_ha: number; quantidade_total: number; custo_total: number }>;
    }>;
    romaneios: Array<{
        id: string; numero_romaneio?: string; data_colheita: string;
        peso_bruto_kg: number; sacas_60kg: number; umidade_pct: number;
        impureza_pct: number; destino?: string; receita_total: number;
    }>;
    resumo: {
        total_operacoes: number; custo_total_operacoes: number;
        total_insumos_aplicados: number; total_colhido_sacas: number; receita_total: number;
    };
}

const fmt = (v: number) => `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

function tipoIcon(tipo: string) {
    if (tipo === "PLANTIO") return <Sprout size={16} className="text-green-600" />;
    if (tipo === "COLHEITA") return <Wheat size={16} className="text-amber-600" />;
    if (tipo.includes("APLICACAO") || tipo === "PULVERIZACAO") return <FlaskConical size={16} className="text-blue-600" />;
    if (tipo === "ADUBACAO") return <Layers size={16} className="text-orange-600" />;
    return <Tractor size={16} className="text-muted-foreground" />;
}

function printEtiqueta(cadeia: Cadeia) {
    const { lote, safra, talhao } = cadeia;
    const trackUrl = lote.qr_code_url ?? `https://api.agrosaas.com/v1/public/track/${lote.codigo_lote}`;
    const qrSrc = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(trackUrl)}`;

    const certs = lote.certificacoes?.length
        ? `<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;">${lote.certificacoes.map(c =>
            `<span style="background:#dcfce7;color:#166534;border-radius:4px;padding:2px 6px;font-size:9px;font-weight:700;">${c}</span>`
          ).join("")}</div>`
        : "";

    const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Etiqueta — ${lote.codigo_lote}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Arial', sans-serif; background: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    .label { width: 400px; border: 2px solid #111; border-radius: 8px; padding: 20px; display: flex; gap: 16px; }
    .qr { flex-shrink: 0; }
    .qr img { display: block; border: 1px solid #e5e7eb; border-radius: 4px; }
    .info { flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
    .codigo { font-size: 22px; font-weight: 900; letter-spacing: 1px; color: #111; }
    .produto { font-size: 14px; font-weight: 700; color: #374151; margin-top: 4px; }
    .row { display: flex; justify-content: space-between; font-size: 11px; color: #6b7280; margin-top: 4px; }
    .row strong { color: #111; }
    .divider { border: none; border-top: 1px dashed #d1d5db; margin: 10px 0; }
    .safra { font-size: 10px; color: #6b7280; }
    .footer { margin-top: 10px; font-size: 9px; color: #9ca3af; text-align: center; }
    @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
  </style>
</head>
<body>
  <div class="label">
    <div class="qr">
      <img src="${qrSrc}" width="130" height="130" alt="QR Code" />
    </div>
    <div class="info">
      <div>
        <div class="codigo">${lote.codigo_lote}</div>
        <div class="produto">${lote.produto}${lote.variedade ? ` — ${lote.variedade}` : ""}</div>
        ${certs}
      </div>
      <hr class="divider" />
      <div>
        <div class="row"><span>Quantidade:</span> <strong>${lote.quantidade_total.toLocaleString("pt-BR")} ${lote.unidade}</strong></div>
        <div class="row"><span>Status:</span> <strong>${lote.status}</strong></div>
        <div class="row"><span>Safra:</span> <strong>${safra.cultura ?? 'Safra'} ${safra.ano_safra}</strong></div>
        ${talhao ? `<div class="row"><span>Talhão:</span> <strong>${talhao.nome}</strong></div>` : ""}
        <div class="row"><span>Gerado em:</span> <strong>${new Date(lote.data_geracao).toLocaleDateString("pt-BR")}</strong></div>
      </div>
      <div class="footer">${trackUrl}</div>
    </div>
  </div>
  <script>window.onload = () => { window.print(); }<\/script>
</body>
</html>`;

    const win = window.open("", "_blank", "width=520,height=380");
    if (win) {
        win.document.write(html);
        win.document.close();
    }
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function RastreabilidadePage() {
    const { activeFazendaId } = useAppStore();
    const [selectedLoteId, setSelectedLoteId] = useState<string | null>(null);

    const { data: lotes = [], isLoading: loadingLotes } = useQuery<Lote[]>({
        queryKey: ["lotes_rastreabilidade", activeFazendaId],
        queryFn: () => apiFetch("/rastreabilidade/lotes"),
        enabled: !!activeFazendaId,
    });

    const { data: certificacoes = [] } = useQuery<any[]>({
        queryKey: ["certificacoes", activeFazendaId],
        queryFn: () => apiFetch(`/rastreabilidade/certificacoes?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId,
    });

    const { data: cadeia, isLoading: loadingCadeia } = useQuery<Cadeia>({
        queryKey: ["cadeia-rastreabilidade", selectedLoteId],
        queryFn: () => apiFetch(`/rastreabilidade/lotes/${selectedLoteId}/cadeia`),
        enabled: !!selectedLoteId,
    });

    const certValidas = certificacoes.filter((c: any) => c.status === "VALIDA").length;

    return (
        <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-boldflex items-center gap-2">
                        <QrCode className="h-8 w-8 text-primary" />
                        Rastreabilidade & Certificações
                    </h2>
                    <p className="text-muted-foreground text-sm mt-1">
                        Cadeia completa: lote → safra → talhão → operações + insumos → colheita.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm"><FileCheck className="size-4 mr-2" /> Auditoria</Button>
                    <Button size="sm"><Plus className="size-4 mr-2" /> Novo Lote</Button>
                </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-primary/5 border-primary/10">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-primary">Conformidade</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">94%</div>
                        <Progress value={94} className="h-2 mt-2" />
                        <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                            <ShieldCheck className="w-3 h-3 text-green-500" /> 2 pendências menores
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Lotes Rastreáveis</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{lotes.length}</div>
                        <p className="text-xs text-muted-foreground mt-1">Clique em "Ver Cadeia" para rastrear</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Certificações Ativas</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{certValidas}</div>
                        <p className="text-xs text-muted-foreground mt-1">Certificações válidas cadastradas</p>
                    </CardContent>
                </Card>
            </div>

            <Tabs defaultValue="lotes" className="w-full">
                <TabsList className="bg-muted/50 p-1">
                    <TabsTrigger value="lotes" className="gap-2">
                        <History className="size-4" /> Lotes de Produção
                    </TabsTrigger>
                    <TabsTrigger value="certificacoes" className="gap-2">
                        <Award className="size-4" /> Certificações & Selos
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="lotes" className="mt-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Histórico de Rastreamento</CardTitle>
                            <CardDescription>
                                Cada lote registra a cadeia completa do campo ao destino final.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                {loadingLotes ? (
                                    Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)
                                ) : lotes.length === 0 ? (
                                    <div className="text-center py-12 border-2 border-dashed rounded-sm">
                                        <QrCode className="mx-auto h-12 w-12 text-muted-foreground/40" />
                                        <h3 className="mt-4 text-lg font-semibold">Nenhum lote gerado</h3>
                                        <p className="text-muted-foreground text-sm">
                                            Inicie a colheita para gerar os primeiros lotes rastreáveis.
                                        </p>
                                    </div>
                                ) : (
                                    lotes.map(lote => (
                                        <div
                                            key={lote.id}
                                            className="flex items-center justify-between p-4 rounded-sm border bg-muted/20 hover:bg-muted/40 transition-colors"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className="bg-white dark:bg-background p-2 rounded-sm shadow-sm border">
                                                    <QrCode className="h-7 w-7 text-foreground" />
                                                </div>
                                                <div>
                                                    <p className="font-bold text-sm">{lote.codigo_lote}</p>
                                                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                                                        <span className="flex items-center gap-1">
                                                            <Package size={11} /> {lote.produto}
                                                            {lote.variedade && ` — ${lote.variedade}`}
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Calendar size={11} /> {new Date(lote.data_geracao).toLocaleDateString("pt-BR")}
                                                        </span>
                                                    </div>
                                                    {lote.certificacoes?.length > 0 && (
                                                        <div className="flex gap-1 mt-1">
                                                            {lote.certificacoes.map(c => (
                                                                <Badge key={c} className="text-[9px] h-4 px-1 bg-green-100 text-green-700 border-none">{c}</Badge>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="hidden md:flex flex-col items-end">
                                                    <span className="text-sm font-bold">{lote.quantidade_total.toLocaleString("pt-BR")} {lote.unidade}</span>
                                                    <StatusBadge
                                                        status={lote.status === "ATIVO" ? "ativo" : "inativo"}
                                                        label={lote.status}
                                                    />
                                                </div>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    className="gap-1 text-xs"
                                                    onClick={() => setSelectedLoteId(lote.id)}
                                                >
                                                    Ver Cadeia <ChevronRight size={14} />
                                                </Button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="certificacoes" className="mt-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {certificacoes.length === 0 ? (
                            <Card className="col-span-2 flex flex-col items-center justify-center border-dashed p-12">
                                <Award className="h-10 w-10 text-muted-foreground/40 mb-3" />
                                <p className="font-bold">Nenhuma certificação cadastrada</p>
                            </Card>
                        ) : (
                            certificacoes.map((c: any) => (
                                <Card key={c.id} className="overflow-hidden">
                                    <div className={`h-1.5 w-full ${c.status === "VALIDA" ? "bg-green-500" : c.status === "EXPIRADA" ? "bg-red-500" : "bg-amber-500"}`} />
                                    <CardHeader className="flex flex-row items-center justify-between space-y-0">
                                        <div>
                                            <CardTitle className="text-base">{c.nome}</CardTitle>
                                            <CardDescription>{c.extensao}</CardDescription>
                                        </div>
                                        <Badge className={c.status === "VALIDA" ? "bg-green-100 text-green-700 border-none" : "bg-red-100 text-red-700 border-none"}>
                                            {c.status}
                                        </Badge>
                                    </CardHeader>
                                    <CardContent className="space-y-2 text-sm">
                                        {c.numero_registro && (
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Registro:</span>
                                                <span className="font-mono text-xs">{c.numero_registro}</span>
                                            </div>
                                        )}
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Validade:</span>
                                            <span className="font-medium">{new Date(c.data_validade).toLocaleDateString("pt-BR")}</span>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))
                        )}
                        <Card className="flex flex-col items-center justify-center border-dashed p-10 hover:bg-muted/30 transition-colors cursor-pointer">
                            <Plus className="h-6 w-6 text-primary mb-2" />
                            <p className="font-bold text-sm">Adicionar Certificação</p>
                        </Card>
                    </div>
                </TabsContent>
            </Tabs>

            {/* ── Sheet: Cadeia de Rastreabilidade ── */}
            <Sheet open={!!selectedLoteId} onOpenChange={open => !open && setSelectedLoteId(null)}>
                <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
                    <SheetHeader className="mb-6">
                        <div className="flex items-start justify-between">
                            <div>
                                <SheetTitle className="flex items-center gap-2 text-xl">
                                    <QrCode className="text-primary" size={20} />
                                    Cadeia de Rastreabilidade
                                </SheetTitle>
                                <SheetDescription>
                                    {cadeia?.lote.codigo_lote} — {cadeia?.lote.produto}
                                </SheetDescription>
                            </div>
                            {cadeia && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="gap-1.5 text-xs shrink-0"
                                    onClick={() => printEtiqueta(cadeia)}
                                >
                                    <Printer size={14} /> Imprimir Etiqueta
                                </Button>
                            )}
                        </div>
                    </SheetHeader>

                    {loadingCadeia ? (
                        <div className="space-y-4">
                            {Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
                        </div>
                    ) : cadeia ? (
                        <div className="space-y-6">
                            {/* Resumo */}
                            <div className="grid grid-cols-2 gap-3">
                                <div className="bg-muted/30 rounded-sm p-3 text-center">
                                    <p className="text-[10px] font-black uppercase text-muted-foreground">Sacas Colhidas</p>
                                    <p className="text-xl font-black">{cadeia.resumo.total_colhido_sacas.toLocaleString("pt-BR")}</p>
                                </div>
                                <div className="bg-muted/30 rounded-sm p-3 text-center">
                                    <p className="text-[10px] font-black uppercase text-muted-foreground">Receita Total</p>
                                    <p className="text-xl font-black">{fmt(cadeia.resumo.receita_total)}</p>
                                </div>
                                <div className="bg-muted/30 rounded-sm p-3 text-center">
                                    <p className="text-[10px] font-black uppercase text-muted-foreground">Custo Operacional</p>
                                    <p className="text-lg font-bold text-red-600">{fmt(cadeia.resumo.custo_total_operacoes)}</p>
                                </div>
                                <div className="bg-muted/30 rounded-sm p-3 text-center">
                                    <p className="text-[10px] font-black uppercase text-muted-foreground">Operações</p>
                                    <p className="text-xl font-black">{cadeia.resumo.total_operacoes}</p>
                                </div>
                            </div>

                            <Separator />

                            {/* Timeline */}
                            <div className="relative">
                                <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

                                {/* Safra */}
                                <TimelineItem
                                    icon={<Sprout size={14} className="text-green-600" />}
                                    color="bg-green-100"
                                    label="SAFRA"
                                    date={`${cadeia.safra.cultura ?? "—"} ${cadeia.safra.ano_safra}`}
                                >
                                    <p className="text-xs text-muted-foreground">
                                        Área: {cadeia.safra?.area_plantada_ha} ha · Status: {cadeia.safra.status}
                                    </p>
                                    {cadeia.talhao && (
                                        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                                            <MapPin size={10} /> Talhão: {cadeia.talhao.nome} ({cadeia.talhao.area_ha} ha)
                                        </p>
                                    )}
                                </TimelineItem>

                                {/* Operações */}
                                {cadeia.operacoes.map(op => (
                                    <TimelineItem
                                        key={op.id}
                                        icon={tipoIcon(op.tipo)}
                                        color="bg-blue-100"
                                        label={op.tipo}
                                        date={new Date(op.data_realizada).toLocaleDateString("pt-BR")}
                                    >
                                        <p className="text-xs font-medium truncate">{op.descricao}</p>
                                        <p className="text-xs text-muted-foreground">
                                            Área: {op.area_aplicada_ha} ha · Custo: {fmt(op.custo_total)}
                                        </p>
                                        {op.insumos.length > 0 && (
                                            <div className="mt-2 space-y-1">
                                                {op.insumos.map((ins, j) => (
                                                    <div key={j} className="flex items-center justify-between text-[11px] bg-muted/30 rounded px-2 py-1">
                                                        <span className="font-medium">{ins.produto_nome}</span>
                                                        <span className="text-muted-foreground">{ins.quantidade_total.toFixed(2)} {ins.unidade}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </TimelineItem>
                                ))}

                                {/* Romaneios */}
                                {cadeia.romaneios.map(rom => (
                                    <TimelineItem
                                        key={rom.id}
                                        icon={<Wheat size={14} className="text-amber-600" />}
                                        color="bg-amber-100"
                                        label={`ROMANEIO ${rom.numero_romaneio ?? ""}`}
                                        date={new Date(rom.data_colheita).toLocaleDateString("pt-BR")}
                                    >
                                        <div className="grid grid-cols-3 gap-1 text-[11px]">
                                            <div><span className="text-muted-foreground">Sacas:</span> <strong>{rom.sacas_60kg.toFixed(0)}</strong></div>
                                            <div><span className="text-muted-foreground">Umidade:</span> <strong>{rom.umidade_pct}%</strong></div>
                                            <div><span className="text-muted-foreground">Impureza:</span> <strong>{rom.impureza_pct}%</strong></div>
                                        </div>
                                        {rom.receita_total > 0 && (
                                            <p className="text-xs font-bold text-green-600 mt-1">{fmt(rom.receita_total)}</p>
                                        )}
                                        {rom.destino && (
                                            <p className="text-xs text-muted-foreground">Destino: {rom.destino}</p>
                                        )}
                                    </TimelineItem>
                                ))}

                                {/* Lote */}
                                <TimelineItem
                                    icon={<QrCode size={14} className="text-primary" />}
                                    color="bg-primary/10"
                                    label="LOTE GERADO"
                                    date={new Date(cadeia.lote.data_geracao).toLocaleDateString("pt-BR")}
                                >
                                    <p className="text-xs font-bold">{cadeia.lote.codigo_lote}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {cadeia.lote.quantidade_total} {cadeia.lote.unidade} · {cadeia.lote.status}
                                    </p>
                                    {cadeia.lote.certificacoes?.length > 0 && (
                                        <div className="flex gap-1 mt-1">
                                            {cadeia.lote.certificacoes.map(c => (
                                                <Badge key={c} className="text-[9px] h-4 px-1 bg-green-100 text-green-700 border-none">{c}</Badge>
                                            ))}
                                        </div>
                                    )}
                                </TimelineItem>
                            </div>
                        </div>
                    ) : null}
                </SheetContent>
            </Sheet>
        </div>
    );
}

// ── Timeline Item ─────────────────────────────────────────────────────────────

function TimelineItem({ icon, color, label, date, children }: {
    icon: React.ReactNode;
    color: string;
    label: string;
    date: string;
    children: React.ReactNode;
}) {
    return (
        <div className="relative pl-10 pb-6">
            <div className={`absolute left-0 flex items-center justify-center w-8 h-8 rounded-full ${color} border border-border z-10`}>
                {icon}
            </div>
            <div className="bg-muted/20 rounded-sm p-3 border border-border/40">
                <div className="flex items-center justify-between mb-1.5">
                    <Badge variant="secondary" className="text-[10px] h-5 font-black">{label}</Badge>
                    <span className="text-[10px] text-muted-foreground">{date}</span>
                </div>
                {children}
            </div>
        </div>
    );
}
