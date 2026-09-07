"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, Leaf, MapPin, FlaskConical, Wheat, Award } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { getApiBaseUrl } from "@/lib/runtime-config";

const API_BASE = getApiBaseUrl();

async function fetchPublic(codigo: string) {
    const res = await fetch(`${API_BASE}/rastreabilidade/track/${codigo}`);
    if (!res.ok) throw new Error("Lote não encontrado");
    return res.json();
}

function fmt(d: string | null) {
    if (!d) return "—";
    return new Date(d + "T00:00:00").toLocaleDateString("pt-BR");
}

export default function TrackPage() {
    const { codigo } = useParams<{ codigo: string }>();

    const { data, isLoading, error } = useQuery({
        queryKey: ["track", codigo],
        queryFn: () => fetchPublic(codigo),
        retry: false,
    });

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gradient-to-b from-green-50 to-white flex items-center justify-center">
                <div className="text-center">
                    <div className="size-12 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                    <p className="text-muted-foreground">Buscando informações do lote…</p>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="min-h-screen bg-gradient-to-b from-red-50 to-white flex items-center justify-center p-6">
                <div className="text-center max-w-sm">
                    <XCircle className="size-16 text-red-400 mx-auto mb-4" />
                    <h1 className="text-xl font-bold mb-2">Lote não encontrado</h1>
                    <p className="text-muted-foreground text-sm">
                        O código <strong>{codigo}</strong> não corresponde a nenhum lote registrado.
                    </p>
                </div>
            </div>
        );
    }

    const lote = data.lote;
    const safra = data.safra;
    const talhao = data.talhao;
    const certificacoes = data.certificacoes ?? [];
    const insumos = data.insumos ?? [];
    const romaneios = data.romaneios ?? [];

    return (
        <div className="min-h-screen bg-gradient-to-b from-green-50 to-white">
            {/* Header */}
            <div className="bg-green-700 text-white py-8 px-6 text-center">
                <div className="max-w-lg mx-auto">
                    <Leaf className="size-10 mx-auto mb-3 opacity-80" />
                    <h1 className="text-2xl font-bold mb-1">Rastreabilidade de Origem</h1>
                    <p className="text-green-200 text-sm">Lote: {lote?.codigo_lote}</p>
                    {lote?.produto_nome && (
                        <p className="text-white font-semibold mt-2 text-lg">{lote.produto_nome}</p>
                    )}
                </div>
            </div>

            <div className="max-w-lg mx-auto px-6 py-8 space-y-6">
                {/* Resumo do lote */}
                <section className="bg-white rounded-xl border shadow-sm p-5">
                    <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">Informações do Lote</h2>
                    <div className="space-y-2">
                        {lote?.quantidade_sacas && (
                            <InfoRow icon={<Wheat className="size-4 text-amber-500" />} label="Quantidade" value={`${lote.quantidade_sacas} sacas (${lote.quantidade_kg?.toLocaleString("pt-BR")} kg)`} />
                        )}
                        {lote?.data_producao && (
                            <InfoRow icon={<CheckCircle2 className="size-4 text-green-500" />} label="Data de Produção" value={fmt(lote.data_producao)} />
                        )}
                        {lote?.destino && (
                            <InfoRow icon={<MapPin className="size-4 text-blue-500" />} label="Destino" value={lote.destino} />
                        )}
                    </div>
                </section>

                {/* Safra e origem */}
                {safra && (
                    <section className="bg-white rounded-xl border shadow-sm p-5">
                        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3 flex items-center gap-2">
                            <Leaf className="size-4 text-emerald-500" /> Origem Agrícola
                        </h2>
                        <div className="space-y-2">
                            <InfoRow label="Cultura" value={safra.cultura ?? "—"} />
                            <InfoRow label="Safra" value={safra.ano_safra} />
                            {talhao && <InfoRow icon={<MapPin className="size-4 text-blue-400" />} label="Talhão de Origem" value={talhao.nome} />}
                        </div>
                    </section>
                )}

                {/* Insumos aplicados */}
                {insumos.length > 0 && (
                    <section className="bg-white rounded-xl border shadow-sm p-5">
                        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3 flex items-center gap-2">
                            <FlaskConical className="size-4 text-purple-500" /> Insumos Aplicados
                        </h2>
                        <div className="space-y-2">
                            {insumos.map((ins: any, i: number) => (
                                <div key={i} className="flex items-center justify-between">
                                    <span className="text-sm">{ins.nome ?? "Insumo"}</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground">{ins.dose_por_ha} {ins.unidade}/ha</span>
                                        {ins.carencia_dias && (
                                            <Badge variant="outline" className="text-xs">carência {ins.carencia_dias}d</Badge>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Certificações */}
                {certificacoes.length > 0 && (
                    <section className="bg-white rounded-xl border shadow-sm p-5">
                        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3 flex items-center gap-2">
                            <Award className="size-4 text-rose-500" /> Certificações
                        </h2>
                        <div className="space-y-2">
                            {certificacoes.map((c: any, i: number) => (
                                <div key={i} className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {c.valida ? (
                                            <CheckCircle2 className="size-4 text-green-500" />
                                        ) : (
                                            <XCircle className="size-4 text-red-400" />
                                        )}
                                        <span className="text-sm font-medium">{c.tipo}</span>
                                    </div>
                                    <span className={cn("text-xs", c.valida ? "text-green-600" : "text-red-500")}>
                                        {c.valida ? `válida até ${fmt(c.data_validade)}` : "expirada"}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Rodapé */}
                <p className="text-center text-xs text-muted-foreground pb-4">
                    Informações verificadas pelo sistema AgroSaaS · {new Date().toLocaleDateString("pt-BR")}
                </p>
            </div>
        </div>
    );
}

function InfoRow({ icon, label, value }: { icon?: React.ReactNode; label: string; value: string }) {
    return (
        <div className="flex items-center justify-between py-0.5">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                {icon}
                {label}
            </div>
            <span className="text-sm font-medium text-right max-w-[60%] truncate">{value}</span>
        </div>
    );
}
