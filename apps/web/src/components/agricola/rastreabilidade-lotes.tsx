"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, QrCode, ExternalLink, ChevronRight, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { useHasTier } from "@/hooks/use-has-tier";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Lock } from "lucide-react";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

interface Lote {
    id: string;
    codigo_lote: string;
    safra_id: string;
    talhao_id: string | null;
    produto_nome: string | null;
    quantidade_kg: number | null;
    quantidade_sacas: number | null;
    data_producao: string | null;
    data_validade: string | null;
    destino: string | null;
    status: string;
    qr_code_url: string | null;
    certificacoes: string[];
    created_at: string;
}

interface Safra { id: string; cultura: string; ano_safra: string; }

interface CadeiaLote {
    safra?: {
        cultura?: string | null;
        ano_safra: string;
        status: string;
    };
    talhao?: {
        nome: string;
        area_hectares?: number | null;
    };
    operacoes?: Array<{
        tipo: string;
        fase_safra?: string | null;
        data_realizada?: string | null;
    }>;
    insumos?: Array<{
        nome?: string | null;
        insumo_id?: string | null;
        dose_por_ha?: string | number | null;
        unidade?: string | null;
        carencia_dias?: number | null;
    }>;
    romaneios?: Array<{
        numero_romaneio?: string | null;
        umidade_pct?: number | null;
        sacas_60kg?: number | null;
    }>;
    certificacoes?: Array<{
        valida: boolean;
        tipo: string;
        data_validade?: string | null;
    }>;
}

interface Props {
    safraId?: string;
    safras?: Safra[];
}

const STATUS_COLOR: Record<string, string> = {
    ATIVO: "bg-green-100 text-green-700",
    VENDIDO: "bg-gray-100 text-gray-700",
    CANCELADO: "bg-red-100 text-red-700",
};

function fmt(d: string | null) {
    if (!d) return "—";
    return new Date(d + "T00:00:00").toLocaleDateString("pt-BR");
}

export function RastreabilidadeLotes({ safraId, safras = [] }: Props) {
    const qc = useQueryClient();
    const hasEnterpriseTier = useHasTier("ENTERPRISE");
    const [open, setOpen] = useState(false);
    const [detalheId, setDetalheId] = useState<string | null>(null);
    const [filtroSafra, setFiltroSafra] = useState(safraId ?? "");

    const [form, setForm] = useState({
        safra_id: safraId ?? "",
        produto_nome: "",
        quantidade_kg: "",
        quantidade_sacas: "",
        data_producao: new Date().toISOString().slice(0, 10),
        data_validade: "",
        destino: "",
    });

    useMonetizationPromptTracking(!hasEnterpriseTier, {
        feature: "agricola.rastreabilidade.lotes",
        surface: "agricola.rastreabilidade.panel",
        requiredTier: "ENTERPRISE",
        ctaLabel: "Ver planos",
    });

    const queryKey = ["lotes-rastreabilidade", filtroSafra];
    const { data: lotes = [], isLoading } = useQuery<Lote[]>({
        queryKey,
        queryFn: () => apiFetch(`/rastreabilidade/lotes${filtroSafra ? `?safra_id=${filtroSafra}` : ""}`),
        enabled: hasEnterpriseTier,
    });

    const { data: cadeia, isLoading: loadingCadeia } = useQuery<CadeiaLote>({
        queryKey: ["cadeia-rastreabilidade", detalheId],
        queryFn: () => apiFetch<CadeiaLote>(`/rastreabilidade/lotes/${detalheId}/cadeia`),
        enabled: !!detalheId && hasEnterpriseTier,
    });

    const criar = useMutation({
        mutationFn: (body: object) => {
            if (!hasEnterpriseTier) {
                trackMonetizationEvent("monetization_blocked", {
                    feature: "agricola.rastreabilidade.lotes.create",
                    surface: "agricola.rastreabilidade.panel",
                    requiredTier: "ENTERPRISE",
                    ctaLabel: "Novo Lote",
                    reason: "mutation_guard",
                });
                throw new Error("Recurso disponível no plano ENTERPRISE.");
            }
            return apiFetch("/rastreabilidade/lotes", { method: "POST", body: JSON.stringify(body) });
        },
        onSuccess: () => {
            toast.success("Lote criado com QR code.");
            qc.invalidateQueries({ queryKey });
            setOpen(false);
        },
        onError: () => toast.error("Erro ao criar lote."),
    });

    function handleCriar() {
        if (!form.safra_id) { toast.error("Selecione uma safra."); return; }
        const body: Record<string, unknown> = {
            safra_id: form.safra_id,
        };
        if (form.produto_nome) body.produto_nome = form.produto_nome;
        if (form.quantidade_kg) body.quantidade_kg = parseFloat(form.quantidade_kg);
        if (form.quantidade_sacas) body.quantidade_sacas = parseFloat(form.quantidade_sacas);
        if (form.data_producao) body.data_producao = form.data_producao;
        if (form.data_validade) body.data_validade = form.data_validade;
        if (form.destino) body.destino = form.destino;
        criar.mutate(body);
    }

    const loteDetalhe = lotes.find(l => l.id === detalheId);

    if (!hasEnterpriseTier) {
        return (
            <Alert className="rounded-sm">
                <Lock className="size-4" />
                <AlertTitle>Rastreabilidade disponível no ENTERPRISE</AlertTitle>
                <AlertDescription className="space-y-3">
                    <p>O plano atual mantém a operação agrícola básica. Lotes auditáveis, cadeia de rastreio e certificações exigem tier ENTERPRISE.</p>
                    <Button
                        asChild
                        size="sm"
                        className="rounded-sm"
                        onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                            feature: "agricola.rastreabilidade.lotes",
                            surface: "agricola.rastreabilidade.panel",
                            requiredTier: "ENTERPRISE",
                            ctaLabel: "Ver planos",
                        })}
                    >
                        <Link href="/dashboard/settings/billing">Ver planos</Link>
                    </Button>
                </AlertDescription>
            </Alert>
        );
    }

    return (
        <div className="space-y-6">
            {/* Filtro e ações */}
            <div className="flex items-center gap-3 flex-wrap">
                {!safraId && safras.length > 0 && (
                    <Select value={filtroSafra} onValueChange={setFiltroSafra}>
                        <SelectTrigger className="h-8 min-w-48 rounded-sm border-border bg-background px-3 text-sm">
                            <SelectValue placeholder="Todas as safras" />
                        </SelectTrigger>
                        <SelectContent className="rounded-sm">
                            {safras.map(s => (
                                <SelectItem key={s.id} value={s.id}>{s.cultura} — {s.ano_safra}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                )}
                <div className="ml-auto">
                    <Button size="sm" onClick={() => { setForm(p => ({ ...p, safra_id: filtroSafra || safraId || "" })); setOpen(true); }}>
                        <Plus className="size-4 mr-1" /> Novo Lote
                    </Button>
                </div>
            </div>

            {/* Lista de lotes */}
            {isLoading ? (
                <Skeleton className="h-48 w-full" />
            ) : lotes.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-12">
                    Nenhum lote de rastreabilidade registrado.
                </p>
            ) : (
                <div className="space-y-2">
                    {lotes.map(lote => (
                        <Card
                            key={lote.id}
                            className="shadow-sm cursor-pointer hover:bg-muted/30 transition-colors"
                            onClick={() => setDetalheId(lote.id)}
                        >
                            <CardContent className="p-4 flex items-center gap-4">
                                <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                                    <QrCode className="size-5 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className="font-semibold text-sm">{lote.codigo_lote}</span>
                                        <Badge className={cn("text-xs border-0", STATUS_COLOR[lote.status] ?? "bg-muted")}>
                                            {lote.status}
                                        </Badge>
                                        {lote.certificacoes?.map(c => (
                                            <Badge key={c} variant="outline" className="text-xs">{c}</Badge>
                                        ))}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                        {lote.produto_nome ?? "Produto não especificado"}
                                        {lote.quantidade_sacas && ` · ${lote.quantidade_sacas} sc`}
                                        {lote.quantidade_kg && ` · ${lote.quantidade_kg.toLocaleString("pt-BR")} kg`}
                                        {lote.data_producao && ` · Produção: ${fmt(lote.data_producao)}`}
                                        {lote.destino && ` · ${lote.destino}`}
                                    </p>
                                </div>
                                <ChevronRight className="size-4 text-muted-foreground shrink-0" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Modal: Novo Lote */}
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader><DialogTitle>Novo Lote de Rastreabilidade</DialogTitle></DialogHeader>
                    <p className="text-xs text-muted-foreground -mt-2">
                        Um código de lote e QR code serão gerados automaticamente.
                    </p>
                    <div className="grid grid-cols-2 gap-3 py-2">
                        {!safraId && (
                            <div className="col-span-2">
                                <Label className="text-xs">Safra *</Label>
                                <Select value={form.safra_id} onValueChange={(value) => setForm(p => ({ ...p, safra_id: value }))}>
                                    <SelectTrigger className="mt-1 h-8 rounded-sm border-border bg-background px-3 text-sm">
                                        <SelectValue placeholder="Selecione..." />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {safras.map(s => <SelectItem key={s.id} value={s.id}>{s.cultura} — {s.ano_safra}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                        <div className="col-span-2">
                            <Label className="text-xs">Produto / Descrição</Label>
                            <Input className="mt-1 h-8 text-sm" placeholder="ex: Café Colino Natural"
                                value={form.produto_nome} onChange={e => setForm(p => ({ ...p, produto_nome: e.target.value }))} />
                        </div>
                        <div>
                            <Label className="text-xs">Qtd (sacas)</Label>
                            <Input type="number" step="0.1" className="mt-1 h-8 text-sm"
                                value={form.quantidade_sacas} onChange={e => setForm(p => ({ ...p, quantidade_sacas: e.target.value }))} />
                        </div>
                        <div>
                            <Label className="text-xs">Qtd (kg)</Label>
                            <Input type="number" className="mt-1 h-8 text-sm"
                                value={form.quantidade_kg} onChange={e => setForm(p => ({ ...p, quantidade_kg: e.target.value }))} />
                        </div>
                        <div>
                            <Label className="text-xs">Data Produção</Label>
                            <Input type="date" className="mt-1 h-8 text-sm"
                                value={form.data_producao} onChange={e => setForm(p => ({ ...p, data_producao: e.target.value }))} />
                        </div>
                        <div>
                            <Label className="text-xs">Data Validade</Label>
                            <Input type="date" className="mt-1 h-8 text-sm"
                                value={form.data_validade} onChange={e => setForm(p => ({ ...p, data_validade: e.target.value }))} />
                        </div>
                        <div className="col-span-2">
                            <Label className="text-xs">Destino</Label>
                            <Input className="mt-1 h-8 text-sm" placeholder="ex: Exportação, Mercado Interno"
                                value={form.destino} onChange={e => setForm(p => ({ ...p, destino: e.target.value }))} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
                        <Button onClick={handleCriar} disabled={criar.isPending}>
                            {criar.isPending ? "Gerando…" : "Gerar Lote + QR Code"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Modal: Cadeia de Rastreabilidade */}
            <Dialog open={!!detalheId} onOpenChange={v => !v && setDetalheId(null)}>
                <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <QrCode className="size-5" />
                            Cadeia de Rastreabilidade — {loteDetalhe?.codigo_lote}
                        </DialogTitle>
                    </DialogHeader>

                    {loadingCadeia ? (
                        <div className="space-y-3 py-4">
                            {[1,2,3].map(i => <Skeleton key={i} className="h-16 w-full" />)}
                        </div>
                    ) : cadeia ? (
                        <div className="space-y-4 py-2">
                            {/* QR Code + link público */}
                            {loteDetalhe?.qr_code_url && (
                                <div className="flex items-center gap-4 p-3 bg-muted/40 rounded-lg">
                                    <Image
                                        src={loteDetalhe.qr_code_url}
                                        alt="QR Code"
                                        width={80}
                                        height={80}
                                        className="size-20 rounded"
                                        unoptimized
                                    />
                                    <div>
                                        <p className="text-sm font-medium">QR Code de Rastreio</p>
                                        <p className="text-xs text-muted-foreground mb-2">Escaneie para ver a origem do produto</p>
                                        <a
                                            href={`/track/${loteDetalhe.codigo_lote}`}
                                            target="_blank"
                                            className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                                        >
                                            <ExternalLink className="size-3" /> Ver página pública
                                        </a>
                                    </div>
                                </div>
                            )}

                            {/* Safra */}
                            {cadeia.safra && (
                                <CadeiaSection titulo="Safra" cor="emerald">
                                    <Row label="Cultura" value={cadeia.safra.cultura ?? "—"} />
                                    <Row label="Ano" value={cadeia.safra.ano_safra} />
                                    <Row label="Status" value={cadeia.safra.status} />
                                </CadeiaSection>
                            )}

                            {/* Talhão */}
                            {cadeia.talhao && (
                                <CadeiaSection titulo="Talhão / Origem" cor="blue">
                                    <Row label="Nome" value={cadeia.talhao.nome} />
                                    {cadeia.talhao.area_hectares && <Row label="Área" value={`${cadeia.talhao.area_hectares} ha`} />}
                                </CadeiaSection>
                            )}

                            {/* Operações */}
                            {cadeia.operacoes?.length > 0 && (
                                <CadeiaSection titulo={`Operações Agrícolas (${cadeia.operacoes.length})`} cor="amber">
                                    {cadeia.operacoes.map((op, i: number) => (
                                        <div key={i} className="flex items-center justify-between py-1 border-b last:border-0">
                                            <div>
                                                <span className="text-sm font-medium">{op.tipo}</span>
                                                {op.fase_safra && <span className="text-xs text-muted-foreground ml-2">({op.fase_safra})</span>}
                                            </div>
                                            <span className="text-xs text-muted-foreground">{fmt(op.data_realizada)}</span>
                                        </div>
                                    ))}
                                </CadeiaSection>
                            )}

                            {/* Insumos */}
                            {cadeia.insumos?.length > 0 && (
                                <CadeiaSection titulo={`Insumos Aplicados (${cadeia.insumos.length})`} cor="purple">
                                    {cadeia.insumos.map((ins, i: number) => (
                                        <div key={i} className="flex items-center justify-between py-1 border-b last:border-0">
                                            <span className="text-sm">{ins.nome ?? ins.insumo_id}</span>
                                            <div className="text-right">
                                                <span className="text-xs text-muted-foreground">
                                                    {ins.dose_por_ha} {ins.unidade}/ha
                                                </span>
                                                {ins.carencia_dias && (
                                                    <Badge variant="outline" className="ml-2 text-xs">
                                                        carência {ins.carencia_dias}d
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </CadeiaSection>
                            )}

                            {/* Romaneios */}
                            {cadeia.romaneios?.length > 0 && (
                                <CadeiaSection titulo={`Colheita / Romaneios (${cadeia.romaneios.length})`} cor="green">
                                    {cadeia.romaneios.map((r, i: number) => (
                                        <div key={i} className="flex items-center justify-between py-1 border-b last:border-0">
                                            <div>
                                                <span className="text-sm font-medium">{r.numero_romaneio ?? `Romaneio ${i+1}`}</span>
                                                {r.umidade_pct && (
                                                    <span className="text-xs text-muted-foreground ml-2">umidade {r.umidade_pct}%</span>
                                                )}
                                            </div>
                                            <span className="text-sm">{r.sacas_60kg?.toFixed(1)} sc</span>
                                        </div>
                                    ))}
                                </CadeiaSection>
                            )}

                            {/* Certificações */}
                            {cadeia.certificacoes?.length > 0 && (
                                <CadeiaSection titulo="Certificações" cor="rose">
                                    {cadeia.certificacoes.map((c, i: number) => (
                                        <div key={i} className="flex items-center justify-between py-1 border-b last:border-0">
                                            <div className="flex items-center gap-2">
                                                {c.valida ? (
                                                    <CheckCircle2 className="size-4 text-green-500" />
                                                ) : (
                                                    <XCircle className="size-4 text-red-400" />
                                                )}
                                                <span className="text-sm font-medium">{c.tipo}</span>
                                            </div>
                                            <span className="text-xs text-muted-foreground">
                                                válida até {fmt(c.data_validade)}
                                            </span>
                                        </div>
                                    ))}
                                </CadeiaSection>
                            )}
                        </div>
                    ) : null}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDetalheId(null)}>Fechar</Button>
                        {loteDetalhe?.codigo_lote && (
                            <a href={`/track/${loteDetalhe.codigo_lote}`} target="_blank">
                                <Button variant="outline">
                                    <ExternalLink className="size-4 mr-1.5" /> Página Pública
                                </Button>
                            </a>
                        )}
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

const COR_MAP: Record<string, string> = {
    emerald: "border-emerald-200 bg-emerald-50/50",
    blue: "border-blue-200 bg-blue-50/50",
    amber: "border-amber-200 bg-amber-50/50",
    purple: "border-purple-200 bg-purple-50/50",
    green: "border-green-200 bg-green-50/50",
    rose: "border-rose-200 bg-rose-50/50",
};

const TITULO_COR: Record<string, string> = {
    emerald: "text-emerald-700",
    blue: "text-blue-700",
    amber: "text-amber-700",
    purple: "text-purple-700",
    green: "text-green-700",
    rose: "text-rose-700",
};

function CadeiaSection({ titulo, cor, children }: { titulo: string; cor: string; children: React.ReactNode }) {
    return (
        <div className={cn("rounded-lg border p-3", COR_MAP[cor] ?? "border-muted bg-muted/20")}>
            <p className={cn("text-xs font-semibold uppercase tracking-wide mb-2", TITULO_COR[cor] ?? "text-muted-foreground")}>
                {titulo}
            </p>
            {children}
        </div>
    );
}

function Row({ label, value }: { label: string; value: string | number }) {
    return (
        <div className="flex items-center justify-between py-0.5">
            <span className="text-xs text-muted-foreground">{label}</span>
            <span className="text-sm font-medium">{value}</span>
        </div>
    );
}
