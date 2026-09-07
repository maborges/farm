"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { CalendarDays, FileText, FlaskConical, Plus } from "lucide-react";

interface Talhao {
    id: string;
    nome: string;
}

interface AnaliseSolo {
    id: string;
    talhao_id: string;
    data_coleta: string;
    laboratorio?: string | null;
    codigo_amostra?: string | null;
    profundidade_cm?: number | null;
    ph_agua?: number | null;
    v_pct?: number | null;
    created_at: string;
}

function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("pt-BR");
}

function fmtNum(value: number | null | undefined, digits = 1): string {
    if (value === null || value === undefined) return "—";
    return value.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function AnaliseSoloPanel({ talhoes, analises }: { talhoes: Talhao[]; analises: AnaliseSolo[] }) {
    const latestByTalhao = talhoes.map((talhao) => {
        const analyses = analises
            .filter((analise) => analise.talhao_id === talhao.id)
            .sort((a, b) => new Date(b.data_coleta).getTime() - new Date(a.data_coleta).getTime());
        return {
            talhao,
            latest: analyses[0] ?? null,
            total: analyses.length,
        };
    });

    const totalAnalises = analises.filter((analise) => talhoes.some((talhao) => talhao.id === analise.talhao_id)).length;

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">
                    {talhoes.length} talhão(ões) disponível(eis) · {totalAnalises} análise(s) vinculada(s)
                </p>
                <Button asChild>
                    <Link href="/agricola/analises-solo">
                        <Plus className="size-4" />
                        Nova Análise
                    </Link>
                </Button>
            </div>
            {talhoes.length === 0 ? (
                <Alert>
                    <FlaskConical className="size-4" />
                    <AlertTitle>Nenhum talhão encontrado nesta safra</AlertTitle>
                    <AlertDescription>
                        Vincule talhões à safra para visualizar análises de solo aqui.
                    </AlertDescription>
                </Alert>
            ) : (
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {latestByTalhao.map(({ talhao, latest, total }) => (
                        <Card key={talhao.id} className="hover:border-primary transition-colors">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-base">{talhao.nome}</CardTitle>
                                <CardDescription>
                                    {latest ? (
                                        <span className="inline-flex flex-col gap-0.5">
                                            <span className="inline-flex items-center gap-1.5">
                                                <CalendarDays className="size-3.5" />
                                                Última coleta em {fmtDate(latest.data_coleta)}
                                            </span>
                                            <span>{total} análise(s) registrada(s)</span>
                                        </span>
                                    ) : (
                                        "Nenhuma análise cadastrada"
                                    )}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {latest ? (
                                    <div className="space-y-3">
                                        <div className="flex flex-wrap gap-2">
                                            <Badge variant="secondary">pH {fmtNum(latest.ph_agua, 1)}</Badge>
                                            <Badge variant="outline">V% {fmtNum(latest.v_pct, 1)}</Badge>
                                            {latest.profundidade_cm != null && (
                                                <Badge variant="outline">{fmtNum(latest.profundidade_cm, 0)} cm</Badge>
                                            )}
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            {latest.laboratorio ? `Laboratório: ${latest.laboratorio}` : "Sem laboratório informado"}
                                        </p>
                                        <Button size="sm" className="justify-start gap-2" asChild>
                                            <Link href="/agricola/analises-solo">
                                                <FileText className="size-4" />
                                                Ver no módulo completo
                                            </Link>
                                        </Button>
                                    </div>
                                ) : (
                                    <Button size="sm" className="justify-start gap-2" asChild>
                                        <Link href="/agricola/analises-solo">
                                            <FileText className="size-4" />
                                            Cadastrar análise
                                        </Link>
                                    </Button>
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
